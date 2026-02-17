import os
import sys
import time

from PyQt5.QtCore import QSize, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFileDialog,
    QMenu,
    QSystemTrayIcon,
    QStyle,
)
from PyQt5.uic import loadUi

from extractor import (
    extract_archive,
    get_new_archive_path,
    wait_for_download_complete,
    wait_for_new_file,
)


class ArchiveExtractWorker(QThread):
    """Worker that watches a download folder and extracts the first new RAR/ZIP when ready."""

    progress_max = pyqtSignal(int)
    progress_value = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    succeeded = pyqtSignal()

    def __init__(self, download_folder: str, extract_folder: str):
        super().__init__()
        self.download_folder = download_folder
        self.extract_folder = extract_folder

    def run(self):
        initial_files = set(os.listdir(self.download_folder))

        self.status_updated.emit("Download hasn't been started")
        wait_for_new_file(self.download_folder)

        self.status_updated.emit("Download Found")
        current_files = wait_for_download_complete(self.download_folder)
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

        extract_archive(
            archive_path,
            self.extract_folder,
            on_status=on_status,
            on_progress=on_progress,
        )
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
        self._setup_tray()

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

    def _browse_extract_folder(self):
        path = QFileDialog.getExistingDirectory(self, "Select Extraction Folder")
        if path:
            self.FileName2.setText(path)

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
        if not download_folder or not extract_folder:
            return

        self.start.setEnabled(False)
        self._worker = ArchiveExtractWorker(download_folder, extract_folder)
        self._worker.progress_max.connect(self.progressBar.setMaximum)
        self._worker.progress_value.connect(self.progressBar.setValue)
        self._worker.status_updated.connect(self.label_4.setText)
        self._worker.succeeded.connect(self._on_extraction_succeeded)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _on_worker_finished(self):
        self.start.setEnabled(True)
        self._worker = None

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
