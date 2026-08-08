from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup

class ToolOverlay(QWidget):
    def __init__(self, parent):
        super().__init__(parent)

        self.setStyleSheet("""
            background-color: rgba(255, 255, 255, 200);
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