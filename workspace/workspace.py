from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QImage
from PySide6.QtCore import Qt, QPointF, QRectF

from collections import deque

from workspace.components.tool_overlay import ToolOverlay


class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        self.pen_size = 3
        self.pen_color = QColor("black")

        self.actual_screen = QApplication.primaryScreen()
        geo = self.actual_screen.availableGeometry()

        self.canvas = QImage(geo.width(), geo.height(), QImage.Format.Format_ARGB32)
        self.canvas.fill(Qt.GlobalColor.white)

        self.tool_overlay = ToolOverlay(self)

        self.last_mid = None
        self.point_buffer = deque(maxlen=4)

        # --- shape tool state (shared by Line, Rectangle, Ellipse) ---
        self.shape_start = None
        self.shape_preview_end = None

    def mousePressEvent(self, event):
        # left click only
        if event.button() != Qt.MouseButton.LeftButton:
            return

        pos = event.position()

        if self.current_tool in ("Line", "Rectangle", "Ellipse"):
            self.shape_start = pos
            self.shape_preview_end = pos
        else:
            self.point_buffer.clear()
            self.point_buffer.append(pos)
            self.last_mid = pos

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        
        if self.current_tool in ("Line", "Rectangle", "Ellipse"):
            if self.shape_start is not None:
                self.shape_preview_end = event.position()
                self.update()
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
                pen = QPen(self.pen_color, self.pen_size)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

            painter.drawPath(path)
            painter.end()

            self.last_mid = smoothed_pos
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.current_tool in ("Line", "Rectangle", "Ellipse"):
            if self.shape_start is not None:
                end_pos = event.position()
                painter = QPainter(self.canvas)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                pen = QPen(self.pen_color, self.pen_size)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(pen)

                if self.current_tool == "Line":
                    painter.drawLine(self.shape_start, end_pos)
                elif self.current_tool == "Rectangle":
                    rect = QRectF(self.shape_start, end_pos).normalized()
                    painter.drawRect(rect)
                elif self.current_tool == "Ellipse":
                    rect = QRectF(self.shape_start, end_pos).normalized()
                    painter.drawEllipse(rect)

                painter.end()

            self.shape_start = None
            self.shape_preview_end = None
            self.update()
            return

        self.point_buffer.clear()
        self.last_mid = None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.canvas)

        if self.current_tool in ("Line", "Rectangle", "Ellipse") and self.shape_start is not None:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            pen = QPen(QColor("black"), self.pen_size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)

            if self.current_tool == "Line":
                painter.drawLine(self.shape_start, self.shape_preview_end)
            elif self.current_tool == "Rectangle":
                rect = QRectF(self.shape_start, self.shape_preview_end).normalized()
                painter.drawRect(rect)
            elif self.current_tool == "Ellipse":
                rect = QRectF(self.shape_start, self.shape_preview_end).normalized()
                painter.drawEllipse(rect)

    def set_current_tool(self, tool_name):
        self.current_tool = tool_name

    def set_pen_size(self, size):
        self.pen_size = size

    def set_pen_color(self, color):
        self.pen_color = color

    