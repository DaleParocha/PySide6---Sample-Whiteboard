from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QScreen

from workspace.workspace import Workspace

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Wild Draw")

        my_screen = QApplication.primaryScreen()
        available_geometry = my_screen.availableGeometry()

        self.resize(available_geometry.width(), available_geometry.height())

        # assign workspace
        # set workspace to center
        workspace = Workspace()
        self.setCentralWidget(workspace)

   