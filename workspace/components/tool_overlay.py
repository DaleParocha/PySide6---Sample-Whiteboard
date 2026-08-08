from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup

class ToolOverlay(QWidget):
    def __init___(self, parent):
        super().__init__(parent)

        self.setStyleSheet("""
            background-color: rgba(255, 255, 255, 200);
            border-radius: 8px;
        """)

        