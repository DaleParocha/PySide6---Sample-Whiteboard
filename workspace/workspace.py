from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPixmap, QCursor, QPainter, QPen, QColor
from PySide6.QtCore import Qt

class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        self.canvas = QPixmap(800, 600)
        self.canvas.fill(Qt.white)
        

    def mousePressEvent(self, event):
        self.last_pos = event.position()

    def mouseMoveEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        cursor = QCursor()
        
        self.painter = QPainter(self.canvas)
        painter.setPen(QPen(QColor("black"), 3))
        
        x1, y1 = cursor.pos()
        
        painter.drawLine(x1, y1)