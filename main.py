import sys

from PySide6.QtWidgets import QApplication, QWidget, QPushButton
from MainWindow.main_window import MainWindow

if __name__ == "__main__":

    app = QApplication(sys.argv)

    main_window = MainWindow()
    window = main_window

    window.show()

    app.exec()