
from PySide6.QtWidgets import (
    QMessageBox, QDialog, QLineEdit, QFormLayout, QDialogButtonBox
)

class CredentialsDialog(QDialog):
    def __init__(self, config_manager):
        super().__init__()
        self.setWindowTitle("Enter Credentials")
        self.config_manager = config_manager

        self.yid_input = QLineEdit()
        self.yid_input.setMaxLength(6)
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.Password)
        self.pwd_input.setMaxLength(8)
        self.store_input = QLineEdit()
        self.store_input.setMaxLength(7)
        self.lan_input = QLineEdit()

        layout = QFormLayout()
        layout.addRow("YID (6 digits):", self.yid_input)
        layout.addRow("Password (7-8 chars):", self.pwd_input)
        layout.addRow("Store Number (7 digits):", self.store_input)
        layout.addRow("LAN ID:", self.lan_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        layout.addWidget(buttons)

        self.setLayout(layout)

        # Load existing credentials if available
        existing = self.check_existing()
        if existing:
            self.yid_input.setText(existing["yid"])
            self.pwd_input.setText(existing["pwd"])
            self.store_input.setText(existing["store"])
            self.lan_input.setText(existing["lan"])

        self.result = None

    def check_existing(self):
        keys = ["yid", "pwd", "store", "lan"]
        if all(self.config_manager.get(k) for k in keys):
            return {k: self.config_manager.get(k) for k in keys}
        return None

    def save(self):
        """Save all fields to config.json"""
        yid = self.yid_input.text().strip()
        pwd = self.pwd_input.text().strip()
        store = self.store_input.text().strip()
        lan = self.lan_input.text().strip()

        if not (yid and pwd and store and lan):
            QMessageBox.warning(self, "Incomplete", "All fields are required.")
            return

        self.config_manager.set("yid", yid)
        self.config_manager.set("pwd", pwd)
        self.config_manager.set("store", store)
        self.config_manager.set("lan", lan)
        self.result = True
        self.accept()

    def cancel(self):
        """Cancel without saving"""
        self.reject()