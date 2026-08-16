from PySide6.QtWidgets import QWidget, QApplication, QMessageBox, QFileDialog
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QImage, QShortcut, QKeySequence, QPixmap, QCursor
from PySide6.QtCore import Qt, QPointF, QRectF, QLineF, QTimer

from collections import deque

from workspace.components.tool_overlay import ToolOverlay
from workspace.components.zoom_overlay import ZoomOverlay


class Workspace(QWidget):
    def __init__(self):
        super().__init__()

        # starting pen
        self.pen_size = 3
        self.pen_color = QColor("black")
        self.current_tool = "Pen"

        # starting zoom/panning vars
        self.view_offset = QPointF(0, 0)
        self.view_scale = 1.0
        self.panning = False
        self.last_pan_pos = None

        # get screen size
        self.actual_screen = QApplication.primaryScreen()
        geo = self.actual_screen.availableGeometry()

        # drawing data -------------------
        self.strokes = []          # list of dicts. points, color, width
        self.shapes = []           # list of dicts. type, start, end, color, width
        self.current_stroke = None
        self.live_layer = None          
        self.live_layer_painter = None
        self.last_live_screen_pos = None
        self.background_image = None

        # Tile caching
        self.CELL_SIZE = 800   # canvas units per tile, also used as tile pixel size (1:1 baked)
        self.tiles = {}        # (cell_x, cell_y) -> QImage
        self.point_buffer = deque(maxlen=4)
        self.is_dragging = False   # True only while actively drawing/panning a stroke

        # shape tool state (Line, Rectangle, Ellipse)
        self.shape_start = None
        self.shape_preview_end = None

        # grid
        self.show_grid = False   # disabled. noticeable lag, needs further work
        self.grid_spacing = 40
        self.grid_subdivisions = 5

        self.tool_overlay = ToolOverlay(self)
        self.zoom_overlay = ZoomOverlay(self)
        self.update_cursor()

        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._needs_repaint = False
        self._repaint_timer = QTimer(self)
        self._repaint_timer.setInterval(16)   # ~60fps
        self._repaint_timer.timeout.connect(self._flush_repaint)
        self._repaint_timer.start()

        # undo/redo
        self.undo_stack = []
        self.redo_stack = []
        self.max_history = 50

        self.undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        self.undo_shortcut.activated.connect(self.undo)

        self.redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        self.redo_shortcut.activated.connect(self.redo)

        self.save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        self.save_shortcut.activated.connect(self.save_canvas)

        self.load_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        self.load_shortcut.activated.connect(self.load_canvas)

    def request_repaint(self):
        self._needs_repaint = True

    def _flush_repaint(self):
        if self._needs_repaint:
            self._needs_repaint = False
            self.update()

    # tile caching ----------------
    def _cells_for_bbox(self, bbox):
        min_cx = int(bbox.left() // self.CELL_SIZE)
        max_cx = int(bbox.right() // self.CELL_SIZE)
        min_cy = int(bbox.top() // self.CELL_SIZE)
        max_cy = int(bbox.bottom() // self.CELL_SIZE)
        cells = []
        for cx in range(min_cx, max_cx + 1):
            for cy in range(min_cy, max_cy + 1):
                cells.append((cx, cy))
        return cells

    def _get_tile(self, cell):
        tile = self.tiles.get(cell)
        if tile is None:
            tile = QImage(self.CELL_SIZE, self.CELL_SIZE, QImage.Format.Format_ARGB32)
            tile.fill(Qt.GlobalColor.transparent)
            self.tiles[cell] = tile
        return tile

    def _tile_painter(self, cell):
        tile = self._get_tile(cell)
        painter = QPainter(tile)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        # shift so canvas-space coordinates land correctly within this
        # tile's local pixel space (tile (0,0) == cell*CELL_SIZE in canvas space)
        painter.translate(-cell[0] * self.CELL_SIZE, -cell[1] * self.CELL_SIZE)
        return painter

    def _bake_stroke(self, stroke):
        pen = QPen(stroke["color"], stroke["width"])
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)

        for cell in self._cells_for_bbox(stroke["bbox"]):
            painter = self._tile_painter(cell)
            painter.setPen(pen)
            painter.drawPath(stroke["path"])
            painter.end()

    def _bake_shape(self, shape):
        pen = QPen(shape["color"], shape["width"])
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        bbox = QRectF(shape["start"], shape["end"]).normalized()

        for cell in self._cells_for_bbox(bbox):
            painter = self._tile_painter(cell)
            painter.setPen(pen)
            if shape["type"] == "Line":
                painter.drawLine(shape["start"], shape["end"])
            elif shape["type"] == "Rectangle":
                painter.drawRect(bbox)
            else:
                painter.drawEllipse(bbox)
            painter.end()

    def _rebuild_tiles(self):
        self.tiles = {}
        for stroke in self.strokes:
            self._bake_stroke(stroke)
        for shape in self.shapes:
            self._bake_shape(shape)


    def to_canvas(self, screen_pos):
        return QPointF(
            (screen_pos.x() - self.view_offset.x()) / self.view_scale,
            (screen_pos.y() - self.view_offset.y()) / self.view_scale,
        )

    def to_screen(self, canvas_pos):
        return QPointF(
            canvas_pos.x() * self.view_scale + self.view_offset.x(),
            canvas_pos.y() * self.view_scale + self.view_offset.y(),
        )

    # grid (procedural, unbounded) ----------------
    def draw_grid(self, painter):
        top_left = self.to_canvas(QPointF(0, 0))
        bottom_right = self.to_canvas(QPointF(self.width(), self.height()))

        minor_spacing = self.grid_spacing / self.grid_subdivisions
        minor_pixel_gap = minor_spacing * self.view_scale
        major_pixel_gap = self.grid_spacing * self.view_scale

        if minor_pixel_gap >= 4:
            lines = []
            x = int(top_left.x() // minor_spacing) * minor_spacing
            while x < bottom_right.x():
                lines.append(QLineF(x, top_left.y(), x, bottom_right.y()))
                x += minor_spacing

            y = int(top_left.y() // minor_spacing) * minor_spacing
            while y < bottom_right.y():
                lines.append(QLineF(top_left.x(), y, bottom_right.x(), y))
                y += minor_spacing

            minor_pen = QPen(QColor(150, 150, 150, 35), 1)
            minor_pen.setCosmetic(True)
            painter.setPen(minor_pen)
            painter.drawLines(lines)   # one call instead of hundreds

        if major_pixel_gap >= 2:
            lines = []
            x = int(top_left.x() // self.grid_spacing) * self.grid_spacing
            while x < bottom_right.x():
                lines.append(QLineF(x, top_left.y(), x, bottom_right.y()))
                x += self.grid_spacing

            y = int(top_left.y() // self.grid_spacing) * self.grid_spacing
            while y < bottom_right.y():
                lines.append(QLineF(top_left.x(), y, bottom_right.x(), y))
                y += self.grid_spacing

            major_pen = QPen(QColor(150, 150, 150, 80), 1)
            major_pen.setCosmetic(True)
            painter.setPen(major_pen)
            painter.drawLines(lines)

        axis_pen = QPen(QColor(120, 120, 120, 140), 1.5)
        axis_pen.setCosmetic(True)
        painter.setPen(axis_pen)
        painter.drawLines([
            QLineF(0, top_left.y(), 0, bottom_right.y()),
            QLineF(top_left.x(), 0, bottom_right.x(), 0),
        ])

    def toggle_grid(self):
        self.show_grid = not self.show_grid
        self.update()

    # mouse events ----------------
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.last_pan_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.push_undo_state()
        pos = self.to_canvas(event.position())

        if self.current_tool in ("Line", "Rectangle", "Ellipse"):
            self.shape_start = pos
            self.shape_preview_end = pos
        else:
            is_eraser = self.current_tool == "Eraser"
            width = self.pen_size * 4 if is_eraser else self.pen_size
            path = QPainterPath()
            path.moveTo(pos)
            self.current_stroke = {
                "points": [pos],
                "path": path,
                "bbox": QRectF(pos.x() - width, pos.y() - width, width * 2, width * 2),
                "color": QColor("white") if is_eraser else self.pen_color,
                "width": width,
            }
            self.strokes.append(self.current_stroke)
            self.point_buffer.clear()
            self.point_buffer.append(pos)
            self.is_dragging = True

            self.live_layer = QImage(self.size(), QImage.Format.Format_ARGB32)
            self.live_layer.fill(Qt.GlobalColor.transparent)
            self.live_layer_painter = QPainter(self.live_layer)
            self.live_layer_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.last_live_screen_pos = self.to_screen(pos)

    def mouseMoveEvent(self, event):
        if self.panning:
            delta = event.position() - self.last_pan_pos
            self.view_offset += delta
            self.last_pan_pos = event.position()
            self.request_repaint()
            return

        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if self.current_tool in ("Line", "Rectangle", "Ellipse"):
            if self.shape_start is not None:
                self.shape_preview_end = self.to_canvas(event.position())
                self.request_repaint()
            return

        if self.current_stroke is not None:
            pos = self.to_canvas(event.position())
            self.point_buffer.append(pos)

            avg_x = sum(p.x() for p in self.point_buffer) / len(self.point_buffer)
            avg_y = sum(p.y() for p in self.point_buffer) / len(self.point_buffer)
            new_point = QPointF(avg_x, avg_y)

            self.current_stroke["points"].append(new_point)
            self.current_stroke["path"].lineTo(new_point)

            w = self.current_stroke["width"]
            point_rect = QRectF(new_point.x() - w, new_point.y() - w, w * 2, w * 2)
            self.current_stroke["bbox"] = self.current_stroke["bbox"].united(point_rect)

            # pixelized on live drawing
            # smooth on release
            new_screen_pos = self.to_screen(new_point)
            pen = QPen(self.current_stroke["color"], w * self.view_scale)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self.live_layer_painter.setPen(pen)
            self.live_layer_painter.drawLine(self.last_live_screen_pos, new_screen_pos)
            self.last_live_screen_pos = new_screen_pos

            self.request_repaint()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.current_tool in ("Line", "Rectangle", "Ellipse"):
            if self.shape_start is not None:
                end_pos = self.to_canvas(event.position())
                new_shape = {
                    "type": self.current_tool,
                    "start": self.shape_start,
                    "end": end_pos,
                    "color": self.pen_color,
                    "width": self.pen_size,
                }
                self.shapes.append(new_shape)
                self._bake_shape(new_shape)
            self.shape_start = None
            self.shape_preview_end = None
            self.update()
            return

        if self.current_stroke is not None:
            self._bake_stroke(self.current_stroke)   # bake the FULL accurate vector path

        if self.live_layer_painter is not None:
            self.live_layer_painter.end()
            self.live_layer_painter = None
        self.live_layer = None

        self.current_stroke = None
        self.point_buffer.clear()
        self.is_dragging = False
        self.update()

    # zoom in/out ----------------
    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.15 if angle > 0 else 1 / 1.15
        self.set_zoom(self.view_scale * factor, event.position())

    def set_zoom(self, new_scale, anchor_screen_pos=None):
        if anchor_screen_pos is None:
            anchor_screen_pos = QPointF(self.width() / 2, self.height() / 2)

        old_canvas_pos = self.to_canvas(anchor_screen_pos)
        self.view_scale = max(0.2, min(new_scale, 8))

        new_screen_pos = QPointF(
            old_canvas_pos.x() * self.view_scale + self.view_offset.x(),
            old_canvas_pos.y() * self.view_scale + self.view_offset.y(),
        )
        self.view_offset += anchor_screen_pos - new_screen_pos

        self.zoom_overlay.update_percent(self.view_scale)
        self.update()

    # painting/drawing ----------------
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.white)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.save()
        painter.translate(self.view_offset)
        painter.scale(self.view_scale, self.view_scale)

        #  load canvas
        if self.background_image is not None:
            painter.drawImage(0, 0, self.background_image)

        if self.show_grid:
            self.draw_grid(painter)

        top_left = self.to_canvas(QPointF(0, 0))
        bottom_right = self.to_canvas(QPointF(self.width(), self.height()))
        view_rect = QRectF(top_left, bottom_right).normalized()

        self._draw_tiles(painter, view_rect)
        self._draw_shape_preview(painter)

        painter.restore()

        # live layer is already in screen-space pixels
        if self.live_layer is not None:
            painter.drawImage(0, 0, self.live_layer)

    def _draw_tiles(self, painter, view_rect):
        for cell in self._cells_for_bbox(view_rect):
            tile = self.tiles.get(cell)
            if tile is not None:
                painter.drawImage(cell[0] * self.CELL_SIZE, cell[1] * self.CELL_SIZE, tile)

    def _draw_shapes_vector(self, painter, shapes_list):
        # used only for save_canvas export, not for on-screen rendering
        for shape in shapes_list:
            pen = QPen(shape["color"], shape["width"])
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            if shape["type"] == "Line":
                painter.drawLine(shape["start"], shape["end"])
            else:
                rect = QRectF(shape["start"], shape["end"]).normalized()
                if shape["type"] == "Rectangle":
                    painter.drawRect(rect)
                else:
                    painter.drawEllipse(rect)

    def _draw_shape_preview(self, painter):
        if self.current_tool not in ("Line", "Rectangle", "Ellipse") or self.shape_start is None:
            return

        pen = QPen(QColor("black"), self.pen_size)
        pen.setCosmetic(True)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)

        if self.current_tool == "Line":
            painter.drawLine(self.shape_start, self.shape_preview_end)
        else:
            rect = QRectF(self.shape_start, self.shape_preview_end).normalized()
            if self.current_tool == "Rectangle":
                painter.drawRect(rect)
            else:
                painter.drawEllipse(rect)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    # tool state ----------------
    def set_current_tool(self, tool_name):
        self.current_tool = tool_name
        self.update_cursor()

    def set_pen_size(self, size):
        self.pen_size = size
        self.update_cursor()

    def set_pen_color(self, color):
        self.pen_color = color
        self.update_cursor()

    # undo/redo ----------------
    def push_undo_state(self):
        self.undo_stack.append((len(self.strokes), len(self.shapes)))
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            return

        stroke_count, shape_count = self.undo_stack.pop()

        removed_strokes = self.strokes[stroke_count:]
        removed_shapes = self.shapes[shape_count:]
        self.redo_stack.append((removed_strokes, removed_shapes))

        del self.strokes[stroke_count:]
        del self.shapes[shape_count:]
        self._rebuild_tiles()
        self.update()

    def redo(self):
        if not self.redo_stack:
            return

        removed_strokes, removed_shapes = self.redo_stack.pop()

        # remember where to trim back to if this gets undone again
        self.undo_stack.append((len(self.strokes), len(self.shapes)))

        self.strokes.extend(removed_strokes)
        self.shapes.extend(removed_shapes)
        self._rebuild_tiles()
        self.update()

    # clear ----------------
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
            self.strokes.clear()
            self.shapes.clear()
            self._rebuild_tiles()
            self.update()

    # save ----------------
    def save_canvas(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Whiteboard",
            "",
            "PNG Files (*.png)"
        )
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"

        bounds = self._compute_content_bounds()
        export_image = QImage(int(bounds.width()) + 40, int(bounds.height()) + 40, QImage.Format.Format_ARGB32)
        export_image.fill(Qt.GlobalColor.white)

        painter = QPainter(export_image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(-bounds.x() + 20, -bounds.y() + 20)

        for stroke in self.strokes:
            if len(stroke["points"]) < 2:
                continue
            pen = QPen(stroke["color"], stroke["width"])
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.drawPath(stroke["path"])

        self._draw_shapes_vector(painter, self.shapes)
        painter.end()

        export_image.save(path, "PNG")

    def _compute_content_bounds(self):
        bbox = QRectF(0, 0, 1, 1)
        has_content = False

        for stroke in self.strokes:
            for p in stroke["points"]:
                if not has_content:
                    bbox = QRectF(p, p)
                    has_content = True
                else:
                    bbox = bbox.united(QRectF(p, p))

        for shape in self.shapes:
            for p in (shape["start"], shape["end"]):
                if not has_content:
                    bbox = QRectF(p, p)
                    has_content = True
                else:
                    bbox = bbox.united(QRectF(p, p))

        return bbox

    # load canvas -----------------------
    def load_canvas(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Whiteboard",
            "",
            "PNG Files (*.png)"
        )

        if not path:
            return

        loaded = QImage(path)
        if loaded.isNull():
            QMessageBox.warning(self, "Load Failed", "Could not open that as an image")
            return
        
        self.background_image = loaded
        self.update()

    # cursor preview ----------------
    def update_cursor(self):
        if self.current_tool not in ("Pen", "Eraser"):
            self.setCursor(Qt.CursorShape.CrossCursor)
            return

        if self.current_tool == "Eraser":
            diameter = max(int(self.pen_size * 4), 6)
            outline_color = QColor("black")
            fill_color = QColor(255, 255, 255, 180)
        else:
            diameter = max(int(self.pen_size), 6)
            outline_color = self.pen_color
            fill_color = QColor(self.pen_color.red(), self.pen_color.green(), self.pen_color.blue(), 120)

        padding = 4
        size = diameter + padding * 2

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(outline_color, 1.5))
        painter.setBrush(fill_color)
        painter.drawEllipse(padding, padding, diameter, diameter)
        painter.end()

        cursor = QCursor(pixmap, size // 2, size // 2)
        self.setCursor(cursor)