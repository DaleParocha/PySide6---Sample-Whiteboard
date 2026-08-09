from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QButtonGroup, QSlider, QLabel
)
from PySide6.QtCore import QEvent,  Qt

class ToolOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.setStyleSheet("""
            background-color: rgba(250, 4, 199, 160);
            border: 1px solid rgba(0, 0, 0, 60);
            border-radius: 8px;
        """)

        # outer layout stacks rows top-to-bottom
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(6)

        # size slider 
        slider_row = QHBoxLayout()
        self.size_label = QLabel("Size: 3")
        slider_row.addWidget(self.size_label)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(50)
        self.size_slider.setValue(3)
        self.size_slider.setFixedWidth(150)
        self.size_slider.valueChanged.connect(parent.set_pen_size)
        self.size_slider.valueChanged.connect(self.update_size_label)
        slider_row.addWidget(self.size_slider)

        outer_layout.addLayout(slider_row)

        # tool buttons
        button_row = QHBoxLayout()

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = ["Pen", "Eraser", "Line", "Rectangle", "Ellipse"]
        for i, name in enumerate(tools):
            btn = QPushButton(name)
            btn.setCheckable(True)

            if i == 0:
                btn.setChecked(True)

            btn.clicked.connect(lambda checked, t=name: parent.set_current_tool(t))
            button_row.addWidget(btn)
            self.tool_group.addButton(btn)

        outer_layout.addLayout(button_row)

        parent.set_current_tool(tools[0])
        # size control
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