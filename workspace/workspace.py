from PySide6.QtWidgets import QWidget, QApplication, QMessageBox, QFileDialog
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QImage, QShortcut, QKeySequence, QPixmap
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
        self.canvas.fill(Qt.GlobalColor.transparent)

        # enable grid
        self.show_grid = True
        self.grid_spacing = 40
        self.grid_subdivisions = 5
        self.grid_cache = None
        self.rebuild_grid_cache()
        

        self.tool_overlay = ToolOverlay(self)

        self.last_mid = None
        self.point_buffer = deque(maxlen=4)

        # shape tool state (Line Rectangle Ellipse) ------------
        self.shape_start = None
        self.shape_preview_end = None

        # undo/redo
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 20

        # undo shortcut 
        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo)

        # redo shortcut
        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo)

        # save shortcut
        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_canvas)

        # load shortcut
        self.load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.load_shortcut.activated.connect(self.load_canvas)

    # create grid 2
    def rebuild_grid_cache(self):
        self.grid_cache = QPixmap(self.width(), self.height())
        self.grid_cache.fill(Qt.GlobalColor.transparent)

        painter = QPainter(self.grid_cache)
        self.draw_grid(painter)
        painter.end()

    #  create grid
    def draw_grid(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        minor_spacing = self.grid_spacing / self.grid_subdivisions

        # minor grid ---
        minor_pen = QPen(QColor(150, 150, 150, 35), 1)
        minor_pen.setCosmetic(True)
        painter.setPen(minor_pen)

        x = 0
        while x < self.width():
            painter.drawLine(int(x), 0, int(x), self.height())
            x += minor_spacing

        y = 0
        while y < self.height():
            painter.drawLine(0, int(y), self.width(), int(y))
            y += minor_spacing

        # major grid ---
        major_pen = QPen(QColor(150, 150, 150, 80), 1)
        major_pen.setCosmetic(True)
        painter.setPen(major_pen)

        for x in range(0, self.width(), self.grid_spacing):
            painter.drawLine(x, 0, x, self.height())
        for y in range(0, self.height(), self.grid_spacing):
            painter.drawLine(0, y, self.width(), y)

        # axis ---
        axis_pen = QPen(QColor(120, 120, 120, 140), 1.5)
        axis_pen.setCosmetic(True)
        painter.setPen(axis_pen)

        center_x = round((self.width() / 2) / self.grid_spacing) * self.grid_spacing
        center_y = round((self.height() / 2) / self.grid_spacing) * self.grid_spacing

        painter.drawLine(center_x, 0, center_x, self.height())
        painter.drawLine(0, center_y, self.width(), center_y)

    # toggle grid
    def toggle_grid(self):
        self.show_grid = not self.show_grid
        if self.show_grid and self.grid_cache is None:
            self.rebuild_grid_cache()
        self.update()

    def mousePressEvent(self, event):
        # left click only
        if event.button() != Qt.MouseButton.LeftButton:
            return

        #  check before changes in canvas
        self.push_undo_state() 

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
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear) 
                painter.setPen(QPen(QColor(0, 0, 0, 0), self.pen_size * 4))
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
        painter.fillRect(self.rect(), Qt.GlobalColor.white)

        if self.show_grid and self.grid_cache is not None:
            painter.drawPixmap(0, 0, self.grid_cache)   # one cheap blit, not hundreds of lines

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

    def resizeEvent(self, event):
        self.rebuild_grid_cache()
        super().resizeEvent(event)

    def set_current_tool(self, tool_name):
        self.current_tool = tool_name

    def set_pen_size(self, size):
        self.pen_size = size

    def set_pen_color(self, color):
        self.pen_color = color

    # undo redo ----------------------------------------------------------
    def push_undo_state(self):
        self.undo_stack.append(self.canvas.copy())
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return

        self.redo_stack.append(self.canvas.copy())
        self.canvas = self.undo_stack.pop()
        self.update()

    def redo(self):
        if not self.redo_stack:
            return

        self.undo_stack.append(self.canvas.copy())
        self.canvas = self.redo_stack.pop()
        self.update()

    # clear all -----------------------------------------------------
    def clear_canvas(self):
        reply = QMessageBox.question(
            self,
            "Clear Canvas",
            "This will erase everything on the canvas. Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.push_undo_state()
            self.canvas.fill(Qt.GlobalColor.transparent)
            self.update()

    # save / load
    def save_canvas(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Whiteboard",
            "",
            "PNG Files (*.png)"
        )
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.canvas.save(path, "PNG")

    def load_canvas(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Whiteboard",
            "",
            "PNG Files (*.png)"
        )
        if path:
            loaded = QImage(path)
            if loaded.isNull():
                QMessageBox.warning(self, "Load Failed", "Could not open that as an image.")
                return

            self.push_undo_state()

            canvas_copy = QImage(self.canvas.size(), QImage.Format.Format_ARGB32)
            canvas_copy.fill(Qt.GlobalColor.transparent)

            painter = QPainter(canvas_copy)
            painter.drawImage(0, 0, loaded)
            painter.end()

            self.canvas = canvas_copy
            self.update()        