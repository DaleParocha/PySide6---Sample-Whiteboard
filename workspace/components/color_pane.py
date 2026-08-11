from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtCore import Qt, QSize


class ColorPanel(QWidget):
    def __init__(self, parent_picker):
        super().__init__()
        self.parent_picker = parent_picker
        self.setFixedSize(140, 140)
        self.hue = 0          # 0-359
        self.sat = 255        # 0-255, x-axis
        self.val = 255        # 0-255, y-axis (inverted: top = bright)

    def set_hue(self, hue):
        self.hue = hue
        self.update()

    def set_marker(self, sat, val):
        self.sat = sat
        self.val = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        sat_gradient = QLinearGradient(0, 0, rect.width(), 0)
        sat_gradient.setColorAt(0, QColor.fromHsv(self.hue, 0, 255))
        sat_gradient.setColorAt(1, QColor.fromHsv(self.hue, 255, 255))
        painter.fillRect(rect, sat_gradient)

        val_gradient = QLinearGradient(0, 0, 0, rect.height())
        val_gradient.setColorAt(0, QColor(0, 0, 0, 0))
        val_gradient.setColorAt(1, QColor(0, 0, 0, 255))
        painter.fillRect(rect, val_gradient)

        x = int((self.sat / 255) * rect.width())
        y = int((1 - self.val / 255) * rect.height())
        painter.setPen(QPen(QColor("white"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(x - 6, y - 6, 12, 12)

    def _pick_at(self, pos):
        x = max(0, min(pos.x(), self.width()))
        y = max(0, min(pos.y(), self.height()))
        self.sat = int((x / self.width()))
        self.val = int((1 - y / self.height() * 255))
        self.update()
        self.parent_picker.on_panel_picked(self.hue, self.sat, self.val)
        