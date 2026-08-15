from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import QEvent, Qt


class ZoomOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.setStyleSheet("""
            QWidget#zoomBox {
                background-color: white;
                border: 1px solid rgba(128, 128, 128, 80);
                border-radius: 8px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background-color: rgba(128, 128, 128, 60);
                border-radius: 4px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                min-width: 50px;
            }
        """)
        self.setObjectName("zoomBox")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        minus_btn = QPushButton("-")
        minus_btn.setFlat(True)
        minus_btn.clicked.connect(self.zoom_out)
        layout.addWidget(minus_btn)

        self.percent_label = QLabel("100%")
        self.percent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.percent_label)

        plus_btn = QPushButton("+")
        plus_btn.setFlat(True)
        plus_btn.clicked.connect(self.zoom_in)
        layout.addWidget(plus_btn)

        parent.installEventFilter(self)
        self.adjustSize()
        self.reposition()

    def zoom_in(self):
        self.parent.set_zoom(self.parent.view_scale * 1.15)

    def zoom_out(self):
        self.parent.set_zoom(self.parent.view_scale / 1.15)

    def update_percent(self, scale):
        self.percent_label.setText(f"{round(scale * 100)}%")

    def reposition(self):
        margin = 20
        parent = self.parentWidget()
        if parent is None:
            return
        x = parent.width() - self.width() - margin
        y = parent.height() - self.height() - margin
        self.move(x, y)

    def eventFilter(self, watched, event):
        if watched == self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.reposition()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        self.reposition()
        super().resizeEvent(event)