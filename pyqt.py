import sys
import os
from PyQt5 import QtWidgets
from PyQt5.QtCore import QSize, QThread,pyqtSignal
from PyQt5.QtWidgets import QDialog, QApplication, QFileDialog, QSystemTrayIcon, QStyle, QAction, QMenu, QGridLayout, \
    QCheckBox, QSpacerItem, QSizePolicy
from PyQt5.uic import loadUi
import rarfile
import time

folders=[]

class extractrar(QThread):

    setTotalProgress = pyqtSignal(int)
    setCurrentProgress = pyqtSignal(int)
    succeeded = pyqtSignal()
    setLabel_4 = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        download_folder=folders[0]
        extract_folder=folders[1]
        initial_path = set(os.listdir(download_folder))
        path_to_check = set(os.listdir(download_folder))
        while initial_path == path_to_check:
            self.setLabel_4.emit("Download hasnt been started")
            path_to_check = set(os.listdir(download_folder))
        self.setLabel_4.emit("Download Found")
        while 'cr' in path_to_check:
            self.setLabel_4.emit("Download in-progress")
            path_to_check = set(os.listdir(download_folder))
        self.setLabel_4.emit("Download Completed")
        time.sleep(10)
        path_to_check = set(os.listdir(download_folder))
        file = path_to_check - initial_path
        file = list(file)
        file_to_extract = file[0]
        file_to_extract = os.path.join(download_folder, file_to_extract)
        file_to_extract = os.path.normpath(file_to_extract)
        a = rarfile.RarFile(file_to_extract)
        path = file[0].replace('.rar', '')
        path = os.path.join(extract_folder, path)
        path = os.path.normpath(path)
        if not (os.path.exists(path)):
            os.mkdir(path)
        totalnumberoffiles = len(a.namelist())
        self.setTotalProgress.emit(100)
        incrementvalue=100//(totalnumberoffiles)
        startingpoint=0
        for i in a.namelist():
            self.setLabel_4.emit("Extracting {}".format(i))
            a.extract(i, path=path)
            startingpoint+=incrementvalue
            self.setCurrentProgress.emit(startingpoint)
        self.succeeded.emit()

class MainWindow(QDialog):
    check_box = None
    tray_icon = None

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setMinimumSize(QSize(401, 392))
        loadUi("test.ui", self)
        self.setWindowTitle("RAR Automation")
        self.browse.clicked.connect(self.browseFolderforDownloads)
        self.browse_2.clicked.connect(self.browseFolderforExtraction)
        self.start.clicked.connect(self.initExtract)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def browseFolderforDownloads(self):
        fname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')  ##Change the default directory
        self.FileName.setText(fname)



    def browseFolderforExtraction(self):
        fname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Folder')  ##Change the default directory
        self.FileName2.setText(fname)


    def closeEvent(self, event):
        if self.checkBox.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "RAR Automation",
                "Application was minimized to Tray",
                QSystemTrayIcon.Information,
                2000
            )

    def initExtract(self):
        folders.append(self.FileName.text())
        folders.append(self.FileName2.text())
        self.start.setEnabled(False)
        self.extractrar = extractrar()
        self.extractrar.setTotalProgress.connect(self.progressBar.setMaximum)
        self.extractrar.setCurrentProgress.connect(self.progressBar.setValue)
        self.extractrar.setLabel_4.connect(self.label_4.setText)
        self.extractrar.succeeded.connect(self.extractSucceeded)
        self.extractrar.finished.connect(self.extractfinished)
        self.extractrar.start()

    def extractfinished(self):
        self.start.setEnabled(True)
        del self.extractrar

    def extractSucceeded(self):
        self.progressBar.setValue(self.progressBar.maximum())
        self.tray_icon.showMessage(
            "RAR Automation",
            "Extraction is completed",
            QSystemTrayIcon.Information,
            2000
        )



app = QApplication(sys.argv)
mainwindow = MainWindow()
mainwindow.show()
sys.exit(app.exec())