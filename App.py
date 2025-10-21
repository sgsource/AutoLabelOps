import math
import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QSplashScreen, QMessageBox, QDialog, QLabel, QRadioButton, QButtonGroup,
    QLineEdit, QTextEdit, QCheckBox
)
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import Qt
from ConfigManager import ConfigManager
from CredentialsDialog import CredentialsDialog
from MultiWorkerManager import MultiWorkerManager
from PDFParser import Planogram
from POGSearch import get_pog_links, level_of
from Telxon import Telxon
from WorkerThread import WorkerThread
from verify_payload import verify_payload
import Label

"""
Helper to access resources both in development and in PyInstaller executable
"""
def resource_path(relative_path):
    """Get absolute path to resource, works in dev and PyInstaller exe"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath("./assets/")
    return os.path.join(base_path, relative_path)


class MainWindow(QMainWindow):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager

        self.setWindowTitle("AutoLabelOps")
        self.resize(600, 400)
        self.setWindowIcon(QIcon(resource_path("barcode.png")))

        layout = QVBoxLayout()

        # --- Action Buttons ---
        self.edit_creds_btn = QPushButton("Edit Credentials")
        self.edit_creds_btn.clicked.connect(self.edit_credentials)

        layout.addWidget(self.edit_creds_btn)

        # --- Label Size Section ---
        self.size_label = QLabel("Label Size:")
        layout.addWidget(self.size_label)

        self.radio_1inch = QRadioButton("1-INCH")
        self.radio_2inch = QRadioButton("2-INCH")
        self.radio_2inch.setChecked(True)  # Default selection

        self.label_size_group = QButtonGroup()
        self.label_size_group.addButton(self.radio_1inch)
        self.label_size_group.addButton(self.radio_2inch)
        self.label_size_group.buttonClicked.connect(self._update_label_size)

        layout.addWidget(self.radio_1inch)
        layout.addWidget(self.radio_2inch)

        # Data member for label size
        self.label_size = 2

        # --- POG input ---
        self.pog_label = QLabel("Enter POG Number (5–6 digits):")
        self.pog_input = QLineEdit()
        self.pog_input.setMaxLength(6)
        self.pog_input.setPlaceholderText("e.g., 12345 or 123456")
        self.pog_input.returnPressed.connect(self._pog_entered)

        layout.addWidget(self.pog_label)
        layout.addWidget(self.pog_input)

        # --- Visibility ---
        self.visibility = False
        checkbox = QCheckBox("Visible")
        checkbox.toggled.connect(self._on_checkbox_toggle)
        layout.addWidget(checkbox)

        # --- POG Items Info ---
        self.pog_count_label = QLabel("POG Items: 0")
        layout.addWidget(self.pog_count_label)

        self.range_from_input = QLineEdit()
        self.range_from_input.setPlaceholderText("From (1)")
        layout.addWidget(self.range_from_input)

        self.range_to_input = QLineEdit()
        self.range_to_input.setPlaceholderText("To (N)")
        layout.addWidget(self.range_to_input)

        self.status_log = QTextEdit()
        self.status_log.setReadOnly(True)
        layout.addWidget(self.status_log)

        # --- Central Widget ---
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    """
    POG level lookup
    """
    # Pog entered handler
    def _pog_entered(self):
        pog_text = self.pog_input.text().strip()
        if not pog_text.isdigit() or not (5 <= len(pog_text) <= 6):
            QMessageBox.warning(self, "Invalid POG", "POG must be 5 or 6 digits.")
            return

        # Get credentials from config
        yid = self.config_manager.get("yid")
        pwd = self.config_manager.get("pwd")
        if not yid or not pwd:
            QMessageBox.warning(self, "Missing Credentials", "Please set credentials first.")
            return

        creds = (yid, pwd)

        self._telxon_result = None
        self._pog_links_result = None
        self._threads_running = 2

        # Disable input while running
        self.pog_input.setEnabled(False)
        self.status_log.clear()

        """ Getting POG level AND PDFs """
        telxon = Telxon()
        telxon_worker = WorkerThread(
            telxon.get_level,
            pog_text,
            creds,
            self.visibility,
            status_callback=lambda msg: self.append_status(f"[Telxon] {msg}")
        )

        pog_worker = WorkerThread(
            get_pog_links,
            pog_text,
            self.visibility,
            status_callback=lambda msg: self.append_status(f"[POG Search] {msg}")
        )

        manager = MultiWorkerManager(
            [(telxon_worker, 'Level'), (pog_worker, 'POG Search')],
            status_logger=self.append_status,
            final_callback=self._extract_pog_data
        )
        manager.start()
    
    def scan_and_download(self, df_chunk, telxon_instance, label_size, creds, visibility, lan_id, semaphore, status_callback=None):
        telxon_instance.scan_labels(df_chunk, label_size, creds, visibility, status_callback)

        if status_callback:
            status_callback("Waiting for download slot...")

        semaphore.acquire()
        try:
            result = telxon_instance.download(lan_id, visibility, status_callback)
        finally:
            semaphore.release()

        return result  # Will be emitted via WorkerThread.finished
    
    def _extract_pog_data(self, results):
        level, pog_links = results
        self.append_status(f"Level={level}, {len(pog_links)} POG links")

        for _, href in pog_links:
            if level_of(href) == level:
                pog_pdf = href
                break

        planogram = Planogram()
        name = 'POG Extraction'

        # Final callback for this worker
        def pog_final(results):
            pog_df = results[0]  # get_pog returns a single DataFrame
            self.pog_df = pog_df

            num_items = len(pog_df)
            self.pog_count_label.setText(f"POG Items: {num_items}")

            # Set default range
            self.range_from_input.setText("1")
            self.range_to_input.setText(str(num_items))

            self.append_status(f"[POG Extraction] Finished parsing {num_items} items.")
            # Re-enable POG input if desired
            self.pog_input.setEnabled(True)

            from functools import partial
            from PySide6.QtCore import QSemaphore

            n = len(pog_df)
            div_factor = 2
            chunk_size = math.ceil(n // div_factor)
            # chunk_size = n // div_factor
            lan_id = self.config_manager.get('lan')
            semaphore = QSemaphore(1)  # Global semaphore for download()

            chunks = [(pog_df[i:i + chunk_size], Label.Telxon()) for i in range(0, len(pog_df), chunk_size)]

            n = len(pog_df)
            div_factor = 2
            chunk_size = n // div_factor
            lan_id = self.config_manager.get('lan')
            semaphore = QSemaphore(1)  # Global semaphore for download()

            chunks = [(pog_df[i:i + chunk_size], Label.Telxon()) for i in range(0, len(pog_df), chunk_size)]

            worker_tuples = []

            for i, (df_chunk, telxon_instance) in enumerate(chunks):
                label = f"Chunk_{i+1} ({i+1}-{i+chunk_size+1})"

                worker = WorkerThread(
                    self.scan_and_download,
                    df_chunk,
                    telxon_instance,
                    self.label_size,
                    (self.config_manager.get('yid'), self.config_manager.get('pwd')),
                    self.visibility,
                    lan_id,
                    semaphore
                )
                worker_tuples.append((worker, label))

            manager = MultiWorkerManager(
                worker_tuples,
                status_logger=self.append_status,
                per_result_callback=lambda path: self.append_status(f"[Downloaded] {path}")
            )
            manager.start()


        pog_worker = WorkerThread(
            planogram.get_pog,
            pog_pdf,
            status_callback=lambda msg: self.append_status(f"{name} {msg}")
        )
        manager = MultiWorkerManager(
            [(pog_worker, name)],
            status_logger=self.append_status,
            final_callback=pog_final
        )
        manager.start()
    
    """
    Utilities
    """
    def _on_checkbox_toggle(self, checked):
        self.visibility = checked

    # Helper to append messages safely from any thread
    def append_status(self, msg: str):
        self.status_log.append(msg)

    def _update_label_size(self):
        """Update data member when radio button changes"""
        if self.radio_1inch.isChecked():
            self.label_size = 1
        elif self.radio_2inch.isChecked():
            self.label_size = 2

    def edit_credentials(self):
        """Open credentials dialog to modify existing credentials"""
        dlg = CredentialsDialog(self.config_manager)
        dlg.exec()  # Changes saved only if Save pressed


# --------------------------
# App Initialization
# --------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # --- Splash ---
    splash_pix = QPixmap(resource_path("barcode.png"))
    splash = QSplashScreen(splash_pix, Qt.WindowStaysOnTopHint)
    splash.showMessage("Loading AutoLabelOps...", Qt.AlignCenter | Qt.AlignBottom, Qt.black)
    splash.show()
    app.processEvents()

    # --- Verification ---
    success, msg = verify_payload()
    splash.close()
    if not success:
        QMessageBox.critical(None, "Verification Failed", msg)
        sys.exit(1)

    # --- Config / Credentials ---
    config_manager = ConfigManager()
    creds_dialog = CredentialsDialog(config_manager)
    if not creds_dialog.check_existing():
        result = creds_dialog.exec()
        if result != QDialog.Accepted:
            sys.exit(0)  # User canceled, exit app

    # --- Show main window ---
    window = MainWindow(config_manager)
    window.show()
    splash.finish(window)

    sys.exit(app.exec())
