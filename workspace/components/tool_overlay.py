from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QButtonGroup, QSlider, QLabel, QSizePolicy
)
from PySide6.QtCore import QEvent, Qt


class ToolOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.setStyleSheet("""
            QWidget#overlayBox {
                background-color: white;
                border: 1px solid rgba(128, 128, 128, 80);
                border-radius: 8px;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 4px 10px;
            }
            QPushButton:checked {
                background-color: rgba(128, 128, 128, 80);
                border-radius: 4px;
            }
            QLabel {
                background-color: transparent;
                border: none;
            }
        """)
        self.setObjectName("overlayBox")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        # outer layout stacks the slider row above the button row
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 8, 12, 8)
        outer_layout.setSpacing(6)

        # size slider
        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)
        slider_row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.size_label = QLabel("Size: 3")
        self.size_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        slider_row.addWidget(self.size_label)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(50)
        self.size_slider.setValue(3)
        self.size_slider.setFixedWidth(150)
        self.size_slider.valueChanged.connect(parent.set_pen_size)
        self.size_slider.valueChanged.connect(self.update_size_label)
        slider_row.addWidget(self.size_slider)

        slider_row.addStretch(1)
        outer_layout.addLayout(slider_row)

        # tool buttons
        button_row = QHBoxLayout()
        button_row.setSpacing(14)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = ["Pen", "Eraser", "Line", "Rectangle", "Ellipse"]
        for i, name in enumerate(tools):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setFlat(True)
            if i == 0:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=name: parent.set_current_tool(t))
            button_row.addWidget(btn)
            self.tool_group.addButton(btn)

        outer_layout.addLayout(button_row)

        parent.set_current_tool(tools[0])
        parent.set_pen_size(self.size_slider.value())

        parent.installEventFilter(self)
        self.adjustSize()
        self.position_overlay()

    def update_size_label(self, value):
        self.size_label.setText(f"Size: {value}")

    def position_overlay(self):
        margin = 20
        parent = self.parentWidget()
        if parent is None:
            return
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - margin
        self.move(x, y)

    def eventFilter(self, watched, event):
        if watched == self.parentWidget() and event.type() == QEvent.Type.Resize:
            self.position_overlay()
        return super().eventFilter(watched, event)

    def resizeEvent(self, event):
        self.position_overlay()
        super().resizeEvent(event)