import os
import sys
import time

from PyQt5.QtCore import QSize, QSettings, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QMessageBox,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QStyle,
)
from PyQt5.uic import loadUi

from extractor import (
    CancelledError,
    extract_archive,
    get_new_archive_path,
    wait_for_download_complete,
    wait_for_new_file,
)

SETTINGS_ORG = "RARAutomation"
SETTINGS_APP = "RAR Automation"


def validate_folders(download_folder: str, extract_folder: str):
    """Return (True, '') if both folders are valid; else (False, error_message)."""
    if not download_folder or not extract_folder:
        return False, "Please set both Download and Extraction folders."
    if not os.path.isdir(download_folder):
        return False, f"Download folder does not exist or is not a directory:\n{download_folder}"
    if not os.path.isdir(extract_folder):
        return False, f"Extraction folder does not exist or is not a directory:\n{extract_folder}"
    if not os.access(download_folder, os.R_OK):
        return False, f"Cannot read from download folder:\n{download_folder}"
    if not os.access(extract_folder, os.W_OK):
        return False, f"Cannot write to extraction folder:\n{extract_folder}"
    return True, ""


class ArchiveExtractWorker(QThread):
    """Worker that watches a download folder and extracts the first new RAR/ZIP when ready."""

    progress_max = pyqtSignal(int)
    progress_value = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    succeeded = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        download_folder: str,
        extract_folder: str,
        delete_after_extract: bool = False,
    ):
        super().__init__()
        self.download_folder = download_folder
        self.extract_folder = extract_folder
        self.delete_after_extract = delete_after_extract
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def _check_cancelled(self) -> bool:
        return self._cancelled

    def run(self):
        try:
            initial_files = set(os.listdir(self.download_folder))
        except OSError as e:
            self.failed.emit(f"Cannot list download folder: {e}")
            return

        self.status_updated.emit("Download hasn't been started")
        try:
            wait_for_new_file(
                self.download_folder,
                check_cancelled=self._check_cancelled,
            )
        except CancelledError:
            self.status_updated.emit("Cancelled")
            return

        self.status_updated.emit("Download Found")
        try:
            current_files = wait_for_download_complete(
                self.download_folder,
                check_cancelled=self._check_cancelled,
            )
        except CancelledError:
            self.status_updated.emit("Cancelled")
            return

        self.status_updated.emit("Download Completed")
        time.sleep(10)
        current_files = set(os.listdir(self.download_folder))
        archive_path = get_new_archive_path(
            self.download_folder, initial_files, current_files
        )

        if not archive_path:
            self.status_updated.emit("No new RAR or ZIP found")
            return

        def on_status(msg: str):
            self.status_updated.emit(msg)

        def on_progress(value: int, total: int):
            self.progress_max.emit(total)
            self.progress_value.emit(value)

        try:
            extract_archive(
                archive_path,
                self.extract_folder,
                on_status=on_status,
                on_progress=on_progress,
                check_cancelled=self._check_cancelled,
            )
        except CancelledError:
            self.status_updated.emit("Cancelled")
            return
        except Exception as e:
            self.failed.emit(f"Extraction failed: {e}")
            return

        if self.delete_after_extract:
            try:
                os.remove(archive_path)
                self.status_updated.emit("Archive deleted")
            except OSError as e:
                self.failed.emit(f"Extraction completed but could not delete archive: {e}")
                return

        self.succeeded.emit()


class MainWindow(QDialog):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setMinimumSize(QSize(401, 392))
        loadUi("test.ui", self)
        self.setWindowTitle("RAR Automation")

        self.browse.clicked.connect(self._browse_download_folder)
        self.browse_2.clicked.connect(self._browse_extract_folder)
        self.start.clicked.connect(self._start_extraction)

        self._worker = None
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._load_saved_paths()
        self._setup_delete_after_checkbox()
        self._setup_cancel_button()
        self._setup_tray()

    def _load_saved_paths(self):
        download = self._settings.value("download_folder", "", type=str)
        extract = self._settings.value("extract_folder", "", type=str)
        if download:
            self.FileName.setText(download)
        if extract:
            self.FileName2.setText(extract)

    def _save_paths(self):
        self._settings.setValue("download_folder", self.FileName.text().strip())
        self._settings.setValue("extract_folder", self.FileName2.text().strip())

    def _setup_delete_after_checkbox(self):
        self.delete_after_checkbox = QCheckBox("Delete archive after extraction", self)
        self.delete_after_checkbox.setChecked(
            self._settings.value("delete_after_extract", False, type=bool)
        )
        self.delete_after_checkbox.stateChanged.connect(self._save_delete_after_setting)
        try:
            parent = self.start.parent()
            if parent is not None and parent.layout() is not None:
                parent.layout().addWidget(self.delete_after_checkbox)
        except Exception:
            self.delete_after_checkbox.setParent(self)
            self.delete_after_checkbox.setGeometry(20, self.start.y() - 30, 250, 24)

    def _save_delete_after_setting(self):
        self._settings.setValue(
            "delete_after_extract", self.delete_after_checkbox.isChecked()
        )

    def _setup_cancel_button(self):
        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_extraction)
        try:
            parent = self.start.parent()
            if parent is not None and parent.layout() is not None:
                parent.layout().addWidget(self.cancel_btn)
        except Exception:
            self.cancel_btn.setParent(self)
            self.cancel_btn.setGeometry(self.start.x() + self.start.width() + 10, self.start.y(), 80, self.start.height())

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        tray_menu = QMenu()
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def _browse_download_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Download Folder")
        if path:
            self.FileName.setText(path)
            self._save_paths()

    def _browse_extract_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Extraction Folder")
        if path:
            self.FileName2.setText(path)
            self._save_paths()

    def closeEvent(self, event):
        if self.checkBox.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "RAR Automation",
                "Application was minimized to Tray",
                QSystemTrayIcon.Information,
                2000,
            )

    def _start_extraction(self):
        download_folder = self.FileName.text().strip()
        extract_folder = self.FileName2.text().strip()
        ok, err = validate_folders(download_folder, extract_folder)
        if not ok:
            QMessageBox.warning(self, "Invalid folders", err)
            return

        self._save_paths()
        self.start.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        delete_after = self.delete_after_checkbox.isChecked()
        self._worker = ArchiveExtractWorker(
            download_folder, extract_folder, delete_after_extract=delete_after
        )
        self._worker.progress_max.connect(self.progressBar.setMaximum)
        self._worker.progress_value.connect(self.progressBar.setValue)
        self._worker.status_updated.connect(self.label_4.setText)
        self._worker.succeeded.connect(self._on_extraction_succeeded)
        self._worker.failed.connect(self._on_extraction_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _cancel_extraction(self):
        if self._worker is not None:
            self._worker.cancel()

    def _on_worker_finished(self):
        self.start.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._worker = None

    def _on_extraction_failed(self, message: str):
        QMessageBox.critical(self, "RAR Automation", message)

    def _on_extraction_succeeded(self):
        self.progressBar.setValue(self.progressBar.maximum())
        self.tray_icon.showMessage(
            "RAR Automation",
            "Extraction is completed",
            QSystemTrayIcon.Information,
            2000,
        )


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
