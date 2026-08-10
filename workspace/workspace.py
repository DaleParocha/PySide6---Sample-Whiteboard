from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QImage
from PySide6.QtCore import Qt, QPointF

from collections import deque

from workspace.components.tool_overlay import ToolOverlay


class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        self.pen_size = 3

        self.actual_screen = QApplication.primaryScreen()
        geo = self.actual_screen.availableGeometry()

        self.canvas = QImage(geo.width(), geo.height(), QImage.Format.Format_ARGB32)
        self.canvas.fill(Qt.GlobalColor.white)

        self.tool_overlay = ToolOverlay(self)

        self.last_mid = None
        self.point_buffer = deque(maxlen=4)

        # --- Line tool state ---
        self.line_start = None     # where the drag began
        self.line_preview_end = None  # current live end point, while dragging

    def mousePressEvent(self, event):
        pos = event.position()

        if self.current_tool == "Line":
            self.line_start = pos
            self.line_preview_end = pos
        else:
            self.point_buffer.clear()
            self.point_buffer.append(pos)
            self.last_mid = pos

    def mouseMoveEvent(self, event):
        if self.current_tool == "Line":
            if self.line_start is not None:
                self.line_preview_end = event.position()
                self.update()   # repaint to show the live preview, canvas untouched
            return

        if len(self.point_buffer) > 0:
            self.point_buffer.append(event.position())

            avg_x = sum(p.x() for p in self.point_buffer) / len(self.point_buffer)
            avg_y = sum(p.y() for p in self.point_buffer) / len(self.point_buffer)
            smoothed_pos = QPointF(avg_x, avg_y)

            path = QPainterPath()
            path.moveTo(self.last_mid)
            path.lineTo(smoothed_pos)

            painter = QPainter(self.canvas)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            if self.current_tool == "Eraser":
                painter.setPen(QPen(QColor("white"), self.pen_size * 4))
            else:
                pen = QPen(QColor("black"), self.pen_size)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

            painter.drawPath(path)
            painter.end()

            self.last_mid = smoothed_pos
            self.update()

    def mouseReleaseEvent(self, event):
        if self.current_tool == "Line":
            if self.line_start is not None:
                painter = QPainter(self.canvas)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                pen = QPen(QColor("black"), self.pen_size)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.drawLine(self.line_start, event.position())
                painter.end()

            self.line_start = None
            self.line_preview_end = None
            self.update()
            return

        self.point_buffer.clear()
        self.last_mid = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.canvas)

        # draw the live preview ON TOP of the canvas, but never INTO it
        if self.current_tool == "Line" and self.line_start is not None:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("black"), self.pen_size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setStyle(Qt.PenStyle.DashLine)   # dashed = visually distinct from a committed line
            painter.setPen(pen)
            painter.drawLine(self.line_start, self.line_preview_end)

    def set_current_tool(self, tool_name):
        self.current_tool = tool_name

    def set_pen_size(self, size):
        self.pen_size = size