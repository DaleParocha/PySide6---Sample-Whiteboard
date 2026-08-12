from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPen
from PySide6.QtCore import Qt


class ColorPanel(QWidget):
    def __init__(self, parent_picker):
        super().__init__()
        self.parent_picker = parent_picker
        self.setFixedSize(140, 140)
        self.hue = 0
        self.sat = 255
        self.val = 255

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
        self.sat = int((x / self.width()) * 255)
        self.val = int((1 - y / self.height()) * 255)
        self.update()
        self.parent_picker.on_panel_picked(self.hue, self.sat, self.val)

    def mousePressEvent(self, event):
        self._pick_at(event.position())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick_at(event.position())


class ColorPanelWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.panel = ColorPanel(self)
        layout.addWidget(self.panel)

        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setMinimum(0)
        self.hue_slider.setMaximum(359)
        self.hue_slider.setValue(0)
        self.hue_slider.valueChanged.connect(self.on_hue_changed)
        layout.addWidget(self.hue_slider)

        self.r_slider, self.r_label, r_row = self._make_rgb_slider("R")
        self.g_slider, self.g_label, g_row = self._make_rgb_slider("G")
        self.b_slider, self.b_label, b_row = self._make_rgb_slider("B")

        layout.addWidget(r_row)
        layout.addWidget(g_row)
        layout.addWidget(b_row)

        self.r_slider.valueChanged.connect(self.on_rgb_changed)
        self.g_slider.valueChanged.connect(self.on_rgb_changed)
        self.b_slider.valueChanged.connect(self.on_rgb_changed)

        self._apply_color(QColor("black"), from_panel=False, from_rgb=False)

    def _make_rgb_slider(self, label_text):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(f"{label_text}: 0")
        label.setFixedWidth(40)
        row_layout.addWidget(label)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(255)
        row_layout.addWidget(slider)
        return slider, label, row

    def on_panel_picked(self, hue, sat, val):
        color = QColor.fromHsv(hue, sat, val)
        self._apply_color(color, from_panel=True, from_rgb=False)

    def on_hue_changed(self, hue):
        self.panel.set_hue(hue)
        color = QColor.fromHsv(hue, self.panel.sat, self.panel.val)
        self._apply_color(color, from_panel=True, from_rgb=False)

    def on_rgb_changed(self):
        if self._updating:
            return
        color = QColor(self.r_slider.value(), self.g_slider.value(), self.b_slider.value())
        self._apply_color(color, from_panel=False, from_rgb=True)

    def _apply_color(self, color, from_panel, from_rgb):
        self._updating = True

        self.r_slider.setValue(color.red())
        self.g_slider.setValue(color.green())
        self.b_slider.setValue(color.blue())
        self.r_label.setText(f"R: {color.red()}")
        self.g_label.setText(f"G: {color.green()}")
        self.b_label.setText(f"B: {color.blue()}")

        if from_rgb:
            h, s, v, _ = color.getHsv()
            self.hue_slider.blockSignals(True)
            self.hue_slider.setValue(max(h, 0))
            self.hue_slider.blockSignals(False)
            self.panel.hue = max(h, 0)
            self.panel.set_marker(s, v)

        self._updating = False
        self.parent.set_pen_color(color)