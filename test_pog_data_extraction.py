import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt, QEventLoop

from App import MainWindow, ConfigManager

@pytest.fixture(scope="session")
def app():
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    return app

@pytest.fixture
def fresh_window(app):
    config_manager = ConfigManager()
    window = MainWindow(config_manager)
    window.show()
    yield window
    window.close()

def run_pog_test(window, pog_number):
    finished_loop = QEventLoop()
    error_occurred = []

    # Connect to MultiWorkerManager final callback
    original_extract = window._extract_pog_data
    def wrapped_extract(results):
        try:
            original_extract(results)
        finally:
            finished_loop.quit()  # signal that processing is done
    window._extract_pog_data = wrapped_extract

    # Monkey-patch append_status to catch ERROR messages
    original_append = window.append_status
    def append_status_patch(msg):
        original_append(msg)
        if "ERROR" in msg:
            error_occurred.append(msg)
            finished_loop.quit()  # quit immediately on error

    window.append_status = append_status_patch

    # Trigger the POG entry
    window.pog_input.clear()
    QTest.keyClicks(window.pog_input, pog_number)
    QTest.keyClick(window.pog_input, Qt.Key_Return)

    # Wait until either finished or error
    finished_loop.exec_()

    # Restore original methods
    window.append_status = original_append
    window._extract_pog_data = original_extract

    if error_occurred:
        raise RuntimeError(f"Worker failed: {error_occurred[0]}")

@pytest.mark.parametrize("pog_number,expected_items", [
    ("12345", 12),
    ("23456", 8),
    ("34567", 15),
])
def test_pog_processing(fresh_window, pog_number, expected_items):
    run_pog_test(fresh_window, pog_number)

    # Assert the POG dataframe
    pog_df = getattr(fresh_window, "pog_df", None)
    assert pog_df is not None, "POG DataFrame was not created"
    assert len(pog_df) == expected_items
