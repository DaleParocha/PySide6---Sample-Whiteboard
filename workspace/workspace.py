from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPixmap, QCursor, QPainter, QPen, QColor, QPainterPath, QImage
from PySide6.QtCore import Qt, QPointF

from collections import deque

from PySide6.QtWidgets import QWidget

import math
import random

from workspace.components.tool_overlay import ToolOverlay

class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        # get screen measurements
        self.actual_screen = QApplication.primaryScreen()
        #  use availableGeometry due to bug
        geo = self.actual_screen.availableGeometry()

        # reuse to resize canvas
        self.canvas = QImage(geo.width(), geo.height(), QImage.Format.Format_ARGB32)        
        self.canvas.fill(Qt.GlobalColor.white)

        self.tool_overlay = ToolOverlay(self)

        # set mouse last_pos to None while nothing happens
        self.last_pos = None

        self.draw_circle(400, 300, 100)
        self.draw_smoothness_test()

        self.point_buffer = deque(maxlen=4)

    # change upon mouse click
    def mousePressEvent(self, event):
        self.last_pos = event.position()
        self.last_mid = event.position()

        pos = event.position()
        self.point_buffer.clear()
        self.point_buffer.append(pos)
        self.last_mid = pos

    # on moveing mouse
    def mouseMoveEvent(self, event):

        # if mouse clicked/pressed --> logic -->
        if self.last_pos is not None:
            # get mouse current position/coords
            current_pos = event.position()
            mid = (self.last_pos + current_pos) / 2

            path = QPainterPath()
            path.moveTo(self.last_mid)           # start exactly where the last segment ended
            path.quadTo(self.last_pos, mid)      # curve toward mid, using last raw point as control

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

            self.last_mid = mid          # next segment starts here

            #  feature?
            # self.last_raw = current_pos  # next segment's control point

            self.last_pos = current_pos  # next segment's control point

            # update every Move event if last_pos != None
            self.update()

    # on release of mouse press return mouse last_pos to None
    def mouseReleaseEvent(self, event):
        self.last_pos = None
        self.last_mid = None

    # start painting
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawImage(0, 0, self.canvas)

    def set_current_tool(self, tool_name):
        self.current_tool = tool_name

    def draw_circle(self, center_x, center_y, radius, color=QColor("black"), width=3):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        painter.drawEllipse(QPointF(center_x, center_y), radius, radius)

        painter.end()
        self.update()

    def draw_smoothness_test(self):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor("black"), 3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        # --- Test 1: shallow diagonal lines ---
        # Near-horizontal/vertical diagonals show jagged "staircasing" most obviously,
        # since each pixel step is most visible at low angles.
        y = 60
        for angle_deg in [5, 15, 30, 45]:
            angle = math.radians(angle_deg)
            length = 300
            x2 = 60 + length * math.cos(angle)
            y2 = y + length * math.sin(angle)
            painter.drawLine(QPointF(60, y), QPointF(x2, y2))
            y += 60

        # --- Test 2: a perfect circle ---
        # Circles reveal antialiasing quality clearly, since curvature changes
        # continuously — any faceting/jaggedness stands out along the arc.
        painter.drawEllipse(QPointF(500, 150), 90, 90)

        # --- Test 3: simulate a FAST, jagged mouse stroke ---
        # Random big jumps between points, run through your actual quadTo
        # smoothing logic — this tests whether fast real strokes will show
        # gaps or kinks, not just idealized straight/curved shapes.
        points = [QPointF(random.randint(500, 750), random.randint(300, 500)) for _ in range(8)]
        last_pos = points[0]
        last_mid = points[0]
        for current_pos in points[1:]:
            mid = (last_pos + current_pos) / 2
            path = QPainterPath()
            path.moveTo(last_mid)
            path.quadTo(last_pos, mid)
            painter.drawPath(path)
            last_mid = mid
            last_pos = current_pos

        # --- Test 4: tightly packed parallel lines ---
        # Reveals whether thin strokes blur together or stay crisp/distinct
        # at high density — a common failure mode distinct from jaggedness.
        x = 60
        for _ in range(15):
            painter.drawLine(QPointF(x, 450), QPointF(x, 550))
            x += 6

        painter.end()
        self.update()
