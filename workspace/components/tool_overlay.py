from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup
from PySide6.QtCore import QEvent

class ToolOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.setStyleSheet("""
            background-color: rgba(250, 4, 199, 160);
            border: 1px solid rgba(0, 0, 0, 60);
            border-radius: 8px;
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = ["Pen", "Eraser", "Line", "Rectangle", "Ellipse"]
        for i, name in enumerate(tools):
            btn = QPushButton(name)
            btn.setCheckable(True)

            if i == 0:
                btn.setChecked(True)

            btn.clicked.connect(lambda checked, t=name: parent.set_current_tool(t))
            layout.addWidget(btn)
            self.tool_group.addButton(btn)

        parent.set_current_tool(tools[0])

        parent.installEventFilter(self)
        self.adjustSize()
        self.position_overlay()

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