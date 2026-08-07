from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QCursor, QPainter, QPen, QColor
from PySide6.QtCore import Qt

class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        self.canvas = QPixmap(800, 600)
        self.canvas.fill(Qt.GlobalColor.white)

        self.last_pos = None
        

    def mousePressEvent(self, event):
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        current_pos = event.position()        
        painter = QPainter(self.canvas)
        painter.setPen(QPen(QColor("black"), 3))
        painter.drawLine(self.last_pos, current_pos)
        painter.end()

        self.last_pos = current_pos
        self.update()

    def mouseReleaseEvent(self, event):
        self.last_pos = None

    # def paintEvent(self, event):
    #     painter = QPainter(self)
    #     painter.drawPixmap(0, 0, self.canvas)