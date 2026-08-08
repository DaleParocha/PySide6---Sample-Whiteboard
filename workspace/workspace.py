from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPixmap, QCursor, QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt

from workspace.components.tool_overlay import ToolOverlay

class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        # get screen measurements
        self.actual_screen = QApplication.primaryScreen()
        #  use availableGeometry due to bug
        geo = self.actual_screen.availableGeometry()

        # reuse to resize canvas
        self.canvas = QPixmap(geo.width(), geo.height())
        self.canvas.fill(Qt.GlobalColor.white)

        self.tool_overlay = ToolOverlay(self)

        # set mouse last_pos to None while nothing happens
        self.last_pos = None
        

    # change upon mouse click
    def mousePressEvent(self, event):
        self.last_raw = event.position()
        self.last_mid = event.position()

    # on moveing mouse
    def mouseMoveEvent(self, event):

        # if mouse clicked/pressed --> logic -->
        if self.last_pos is not None:
            # get mouse current position/coords
            current_pos = event.position()

            path = QPainterPath()
            path.moveTo(self.last_pos)
            mid = (self.last_pos + current_pos) / 2
            path.quadTo(self.last_pos, mid)


            # paint on canvas
            painter = QPainter(self.canvas)

            # smoothener
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if self.current_tool == "Eraser":
                painter.setPen(QPen(QColor("white"), 20))

            else:
                # customizing pen
                pen = QPen(QColor("black"), 3)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

            # drawLine(x1,y1,x2,y2) --> ((x1, y1),(x2, y2))
            painter.drawPath(path)
            painter.end()

            self.last_pos = current_pos

            # update every Move event if last_pos != None
            self.update()

    # on release of mouse press return mouse last_pos to None
    def mouseReleaseEvent(self, event):
        self.last_raw = None
        self.last_mid = None

    # start painting
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.canvas)

    def set_current_tool(self, tool_name):
        self.current_tool = tool_name
