"""The map region: paints the core's shape list (AD-6) and turns keys and clicks into commands.

The map is drawn in a thread of its own (P2-T14, DP140): the core's scene is
worked out and painted onto an image there, and the widget only shows the
latest image. So the window, the screen reader and the clicks of a held arrow
key never wait for a drawing. A drawing asked for while one is being made is
made next, and only the latest is kept.
"""
from __future__ import annotations

import math
import sys
import threading
import time
import traceback

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QAccessible, QBrush, QColor, QImage, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QAccessibleWidget, QWidget



def _add_outline(path: QPainterPath, points: list, seam) -> None:
    """Outline a ring, lifting the pen over artificial edges (AD-17)."""
    if not seam.any():
        path.addPolygon(QPolygonF(points))
        path.closeSubpath()
        return
    n = len(points)
    start = int(np.argmax(seam)) + 1  # begin just after a seam, so every run is whole
    pen_down = False
    for k in range(n):
        i = (start + k) % n
        if not pen_down:
            path.moveTo(points[i])
            pen_down = True
        if seam[i]:
            pen_down = False
        else:
            path.lineTo(points[(i + 1) % n])


def _paint_lines_and_markers(painter: QPainter, scene: dict) -> None:
    """Line features as strokes, one for each run of points, and point features as
    small round markers (P2-T10a). The core has placed every point already."""
    runs = scene.get("line_runs")
    if runs is not None and len(runs) > 1:
        xy = np.asarray(scene["line_coords"], dtype=np.float64).reshape(-1, 2).tolist()
        pens = [QPen(QColor(s["stroke"]), s["width"]) for s in scene["line_styles"]]
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for k in range(len(runs) - 1):
            painter.setPen(pens[scene["line_style"][k]])
            painter.drawPolyline(QPolygonF([QPointF(x, y) for x, y in xy[runs[k]:runs[k + 1]]]))
    marks = scene.get("marker_style")
    if marks is not None and len(marks):
        xy = np.asarray(scene["marker_coords"], dtype=np.float64).reshape(-1, 2).tolist()
        styles = scene["marker_styles"]
        for k, (x, y) in enumerate(xy):
            s = styles[marks[k]]
            painter.setPen(QPen(QColor(s["stroke"]), 1))
            painter.setBrush(QBrush(QColor(s["fill"])))
            painter.drawEllipse(QPointF(x, y), s["radius"], s["radius"])


def paint_scene(painter: QPainter, scene: dict) -> None:
    """Paint one scene. Used by the widget and by the tests on an image."""
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.fillRect(QRectF(0, 0, scene["width"], scene["height"]), QColor(scene["background"]))
    g = scene["globe"]
    disc = QRectF(g["cx"] - g["r"], g["cy"] - g["r"], 2 * g["r"], 2 * g["r"])
    painter.setPen(QPen(QColor(g["edge"]), 2))
    painter.setBrush(QBrush(QColor(g["fill"])))
    painter.drawEllipse(disc)

    clip = QPainterPath()
    clip.addEllipse(disc)
    painter.setClipPath(clip)

    # A plain list first: making Qt points from NumPy numbers one by one is
    # twice as slow (measured in spike S5).
    coords = np.asarray(scene["coords"], dtype=np.float64).reshape(-1, 2).tolist()
    seam = np.asarray(scene["seam"])
    rings, shapes = scene["rings"], scene["shapes"]
    styles = [(QBrush(QColor(s["fill"])), QPen(QColor(s["stroke"]), s["width"])) for s in scene["styles"]]
    outlines = []
    for si in range(len(shapes) - 1):
        fill = QPainterPath()
        fill.setFillRule(Qt.FillRule.OddEvenFill)
        outline = QPainterPath()
        for ri in range(shapes[si], shapes[si + 1]):
            a, b = rings[ri], rings[ri + 1]
            points = [QPointF(x, y) for x, y in coords[a:b]]
            fill.addPolygon(QPolygonF(points))
            fill.closeSubpath()
            _add_outline(outline, points, seam[a:b])
        brush, pen = styles[scene["shape_style"][si]]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(brush)
        painter.drawPath(fill)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(pen)
        painter.drawPath(outline)
        outlines.append(outline)

    cs = scene["current_style"]
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(QColor(cs["stroke"]), cs["width"]))
    for si in scene["current"]:
        painter.drawPath(outlines[si])
    _paint_lines_and_markers(painter, scene)
    painter.setClipping(False)

    c = scene.get("cross")
    if c:
        for colour, width in ((c["halo"], 4), (c["colour"], 2)):
            painter.setPen(QPen(QColor(colour), width))
            painter.drawLine(QPointF(c["x"] - c["size"], c["y"]), QPointF(c["x"] + c["size"], c["y"]))
            painter.drawLine(QPointF(c["x"], c["y"] - c["size"]), QPointF(c["x"], c["y"] + c["size"]))
    h = scene.get("heading")
    if h:   # the heading arrow at the centre (LOC-7)
        angle = math.radians(h["degrees"])
        tip = QPointF(h["x"] + h["length"] * math.sin(angle), h["y"] - h["length"] * math.cos(angle))
        left = QPointF(h["x"] + 9 * math.sin(angle - 2.5), h["y"] - 9 * math.cos(angle - 2.5))
        right = QPointF(h["x"] + 9 * math.sin(angle + 2.5), h["y"] - 9 * math.cos(angle + 2.5))
        arrow = QPolygonF([tip, left, QPointF(h["x"], h["y"]), right])
        painter.setPen(QPen(QColor(h["halo"]), 3))
        painter.setBrush(QBrush(QColor(h["colour"])))
        painter.drawPolygon(arrow)


class Drawer(QObject):
    """Draws the map in its own thread. request() never waits; drawn is sent,
    in the window's thread, with each finished image."""

    drawn = Signal(QImage)

    def __init__(self, session):
        super().__init__()
        self._session = session
        self._wake = threading.Condition()
        self._wanted: tuple | None = None
        self._busy = False
        self._stopped = False
        self.made = 0
        # The window's timer and the drawing share Python: let them take turns
        # often, so a held key's step is never kept waiting more than a moment.
        sys.setswitchinterval(min(sys.getswitchinterval(), 0.0002))
        self._thread = threading.Thread(target=self._run, name="map drawing", daemon=True)
        self._thread.start()

    def request(self, width: int, height: int, ratio: float) -> None:
        with self._wake:
            self._wanted = (max(1, width), max(1, height), ratio)
            self._wake.notify()

    def idle(self) -> bool:
        with self._wake:
            return self._wanted is None and not self._busy

    def stop(self) -> None:
        with self._wake:
            self._stopped = True
            self._wake.notify()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while True:
            with self._wake:
                while self._wanted is None and not self._stopped:
                    self._wake.wait()
                if self._stopped:
                    return
                width, height, ratio = self._wanted
                self._wanted = None
                self._busy = True
            try:
                image = self._draw(width, height, ratio)
            except Exception:   # a fault in one drawing never stops the map being drawn again
                traceback.print_exc()
                image = None
            with self._wake:
                self._busy = False
                stopped = self._stopped
            if image is not None and not stopped:
                self.made += 1
                self.drawn.emit(image)

    def _draw(self, width: int, height: int, ratio: float) -> QImage:
        scene = self._session.scene(width, height)
        start = time.perf_counter()
        image = QImage(round(width * ratio), round(height * ratio), QImage.Format.Format_ARGB32_Premultiplied)
        image.setDevicePixelRatio(ratio)
        painter = QPainter(image)
        try:
            paint_scene(painter, scene)
        finally:
            painter.end()
        self._session.frame_painted((time.perf_counter() - start) * 1000)
        return image


def _accessible_factory(_key, obj):
    """The map is a pane to screen readers. NVDA says nothing for the pane role
    when focus arrives, so it says only the map's name, which is the place
    under the centre. A plain widget is a "grouping", which NVDA announced
    (PO feedback on spike S5)."""
    if isinstance(obj, MapWidget):
        return QAccessibleWidget(obj, QAccessible.Role.Pane)
    return None


_factory_installed = False


def install_accessible_factory() -> None:
    global _factory_installed
    if not _factory_installed:
        QAccessible.installFactory(_accessible_factory)
        _factory_installed = True


class MapWidget(QWidget):
    def __init__(self, window, session):
        install_accessible_factory()
        super().__init__()
        self._window = window
        self._session = session
        self.setObjectName("map")
        self.setAccessibleName(session.map_label())
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(300, 300)
        self.last_paint_ms: float | None = None
        self.setMouseTracking(True)
        self.grabGesture(Qt.GestureType.PinchGesture)
        self._last = None
        self._image: QImage | None = None
        self._drawer = Drawer(session)
        self._drawer.drawn.connect(self._show)

    def redraw(self) -> None:
        """Ask for the map to be drawn again, at the place as it is now. Never waits."""
        self._drawer.request(self.width(), self.height(), self.devicePixelRatioF())

    def drawing_done(self) -> bool:
        """Nothing waiting to be drawn or shown (for the tests)."""
        return self._drawer.idle()

    @property
    def drawings_made(self) -> int:
        return self._drawer.made

    def stop_drawing(self) -> None:
        self._drawer.stop()

    def _show(self, image: QImage) -> None:
        self._image = image
        self.last_paint_ms = self._session.paint_ms
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.redraw()

    def paintEvent(self, _event):
        painter = QPainter(self)
        try:
            if self._image is not None:
                painter.drawImage(QPointF(0, 0), self._image)   # until the new size is drawn, the last image
            else:
                painter.fillRect(self.rect(), QColor(self._session.scene_background()))
            if self.hasFocus():
                painter.setPen(QPen(QColor("#ffffff"), 3, Qt.PenStyle.DashLine))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(self.rect().adjusted(2, 2, -3, -3))
        finally:
            painter.end()

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.update()

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.refresh_name()
        self.update()

    def refresh_name(self) -> None:
        """Name the map after the place under the centre, but only while it
        does not have focus, so NVDA never reads a name change during turning."""
        if not self.hasFocus():
            self.setAccessibleName(self._session.map_label())

    def event(self, event):
        if event.type() == QEvent.Type.Gesture:
            pinch = event.gesture(Qt.GestureType.PinchGesture)
            if pinch is not None and pinch.state() == Qt.GestureState.GestureFinished:
                scale = pinch.totalScaleFactor()
                if scale > 1.2 or scale < 0.83:  # a pinch changes the zoom to the next in the list (NAV-13)
                    self._window.dispatch("map.zoom_to", direction=-1 if scale > 1 else 1)
            return True
        return super().event(event)

    def keyPressEvent(self, event):
        # Keys are handled once, for the whole window, by MainWindow's key filter (AD-3).
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setFocus()
            self._press = event.position()
            self._last = event.position()
            self._dragged = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and getattr(self, "_last", None) is not None:
            p = event.position()
            dx, dy = p.x() - self._last.x(), p.y() - self._last.y()
            if self._dragged or abs(p.x() - self._press.x()) + abs(p.y() - self._press.y()) > 4:
                self._dragged = True
                self._last = p
                self._window.dispatch("map.drag", dx=dx, dy=dy, width=self.width(), height=self.height())
            event.accept()
            return
        if self._session.settings["hover_announce"]:
            p = event.position()
            self._window.dispatch("map.hover", x=p.x(), y=p.y(), width=self.width(), height=self.height())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and getattr(self, "_last", None) is not None:
            if self._dragged:
                self._window.release_held()
            else:
                p = event.position()
                self._window.dispatch("map.click", x=p.x(), y=p.y(), width=self.width(), height=self.height())
            self._last = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta:
            self._window.dispatch("map.zoom_to", direction=-1 if delta > 0 else 1)  # wheel up zooms in
            event.accept()
            return
        super().wheelEvent(event)
