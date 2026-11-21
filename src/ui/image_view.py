"""Paint an image with a shareable zoom and normalized viewport center."""

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget


def to_qpixmap(img):
    """Convert an OpenCV grayscale or BGR array to an independent QPixmap."""
    img = np.ascontiguousarray(img)
    h, w = img.shape[:2]
    fmt = QImage.Format.Format_Grayscale8 if img.ndim == 2 else QImage.Format.Format_BGR888
    qimg = QImage(img.data, w, h, img.strides[0], fmt)
    return QPixmap.fromImage(qimg.copy())


class ImageView(QWidget):
    viewChanged = Signal(float, bool, QPointF)
    pixelHovered = Signal(int, int, object)

    MAX_ZOOM = 8.0
    ZOOM_STEP = 1.25

    def __init__(self):
        super().__init__()
        self.setMinimumSize(160, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self._image = None
        self._pixmap = None
        self._zoom = 1.0
        self._relative_to_fit = True
        self._center = QPointF(0.5, 0.5)
        self._drag_position = None

    def set_image(self, img):
        """Show an image snapshot while keeping the comparison viewport."""
        if img is not self._image:
            self._pixmap = to_qpixmap(img) if img is not None else None
            self._image = img
            self.update()

    def pixmap(self):
        return self._pixmap

    def text(self):
        return "No image" if self._image is None else ""

    @property
    def zoom_factor(self):
        """Return the displayed scale in screen units per image pixel."""
        fit = self._fit_factor()
        if self._relative_to_fit:
            return min(self.MAX_ZOOM, fit * self._zoom)
        return min(self.MAX_ZOOM, max(min(1.0, fit), self._zoom))

    def set_view(self, zoom, relative_to_fit, center):
        """Receive a shared scale and center expressed as fractions of image dimensions."""
        self._zoom = zoom
        self._relative_to_fit = relative_to_fit
        self._center = center
        self.update()

    def fit_to_window(self):
        self._change_view(1.0, True, QPointF(0.5, 0.5))

    def actual_size(self):
        self._change_view(1.0, False, self._center)

    def zoom_in(self):
        self._zoom_by(self.ZOOM_STEP, self._viewport_center())

    def zoom_out(self):
        self._zoom_by(1 / self.ZOOM_STEP, self._viewport_center())

    def pixel_at(self, position):
        """Return (x, y, gray or BGR) at a widget position, or None in the margins."""
        rect = self._image_rect()
        if rect.isEmpty():
            return None
        scale = self.zoom_factor
        x = (position.x() - rect.left()) / scale
        y = (position.y() - rect.top()) / scale
        if 0 <= x < self._pixmap.width() and 0 <= y < self._pixmap.height():
            x, y = int(x), int(y)
            pixel = self._image[y, x]
            value = int(pixel) if self._image.ndim == 2 else tuple(map(int, pixel))
            return x, y, value
        return None

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#1e1e1e"))
        if self._pixmap is None:
            painter.setPen(QColor("#a0a0a0"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())
            return
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.zoom_factor < 1)
        painter.drawPixmap(self._image_rect(), self._pixmap, QRectF(self._pixmap.rect()))

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if self._pixmap is None or delta == 0:
            event.ignore()
            return
        self._zoom_by(self.ZOOM_STEP ** (delta / 120), event.position())
        event.accept()

    def mousePressEvent(self, event):
        rect = self._image_rect()
        if event.button() == Qt.MouseButton.LeftButton and (
            rect.width() > self.width() or rect.height() > self.height()
        ):
            self._drag_position = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        position = event.position()
        if self._drag_position is not None:
            delta = position - self._drag_position
            self._drag_position = position
            rect = self._image_rect()
            if not rect.isEmpty():
                center = self._bounded_center(
                    self._normalized_position(self._viewport_center() - delta, rect),
                    rect.width(), rect.height(),
                )
                self._change_view(self._zoom, self._relative_to_fit, center)
        pixel = self.pixel_at(position)
        if pixel is not None:
            self.pixelHovered.emit(*pixel)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._drag_position is not None:
            self._drag_position = None
            self.unsetCursor()
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.fit_to_window()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _zoom_by(self, multiplier, anchor):
        rect = self._image_rect()
        if rect.isEmpty():
            return
        old_scale, fit = self.zoom_factor, self._fit_factor()
        minimum = fit if self._relative_to_fit else min(1.0, fit)
        scale = max(minimum, min(self.MAX_ZOOM, old_scale * multiplier))
        if scale == old_scale:
            return
        width, height = self._pixmap.width() * scale, self._pixmap.height() * scale
        # Keep the same image point beneath the anchor as the displayed size changes.
        offset = self._viewport_center() - anchor
        center = self._normalized_position(anchor, rect) + QPointF(
            offset.x() / width, offset.y() / height,
        )
        zoom = scale / fit if self._relative_to_fit else scale
        self._change_view(zoom, self._relative_to_fit, self._bounded_center(center, width, height))

    def _change_view(self, zoom, relative_to_fit, center):
        self.set_view(zoom, relative_to_fit, center)
        self.viewChanged.emit(zoom, relative_to_fit, center)

    def _fit_factor(self):
        if self._pixmap is None or self.width() == 0 or self.height() == 0:
            return 1.0
        return min(self.MAX_ZOOM,
                   self.width() / self._pixmap.width(), self.height() / self._pixmap.height())

    def _image_rect(self):
        if self._pixmap is None:
            return QRectF()
        scale = self.zoom_factor
        width, height = self._pixmap.width() * scale, self._pixmap.height() * scale
        center = self._bounded_center(self._center, width, height)
        corner = self._viewport_center() - QPointF(center.x() * width, center.y() * height)
        return QRectF(corner.x(), corner.y(), width, height)

    def _bounded_center(self, center, width, height):
        # Keep an axis centered when it fits and prevent blank space when panning.
        half_x = min(0.5, self.width() / (2 * width))
        half_y = min(0.5, self.height() / (2 * height))
        return QPointF(
            max(half_x, min(1 - half_x, center.x())),
            max(half_y, min(1 - half_y, center.y())),
        )

    def _viewport_center(self):
        return QPointF(self.width() / 2, self.height() / 2)

    @staticmethod
    def _normalized_position(position, rect):
        return QPointF((position.x() - rect.left()) / rect.width(),
                       (position.y() - rect.top()) / rect.height())
