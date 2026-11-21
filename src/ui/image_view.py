import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


def to_qpixmap(img):
    """OpenCV (BGR veya gray) numpy dizisini QPixmap'e çevirir."""
    if img.ndim == 2:
        img = np.ascontiguousarray(img)
        h, w = img.shape
        qimg = QImage(img.data, w, h, img.strides[0], QImage.Format.Format_Grayscale8)
    else:
        rgb = np.ascontiguousarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        h, w, _ = rgb.shape
        qimg = QImage(rgb.data, w, h, rgb.strides[0], QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())  # copy: numpy belleğinden bağımsız olsun


class ImageView(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(320, 240)
        # Ignored: pixmap büyüdükçe pencerenin kendi kendine büyümesini engeller
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setStyleSheet("background-color: #1e1e1e; color: #888;")
        self._pixmap = None
        self.setText("No image")

    def set_image(self, img):
        if img is None:
            self._pixmap = None
            self.clear()
            self.setText("No image")
            return
        self._pixmap = to_qpixmap(img)
        self._update_view()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_view()

    def _update_view(self):
        if self._pixmap is not None:
            self.setPixmap(self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
