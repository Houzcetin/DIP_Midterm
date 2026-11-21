import os
import cv2
import numpy as np


class ImageState:
    """Original ve current (result) görüntüyü tutar."""

    def __init__(self):
        self.original = None
        self.current = None
        self.path = None

    def has_image(self):
        return self.original is not None

    def load(self, path):
        # cv2.imread Türkçe karakterli yolları (ör. "Masaüstü") okuyamaz,
        # bu yüzden dosyayı byte olarak okuyup imdecode ile çözüyoruz.
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Görüntü okunamadı: {path}")

        # Alpha kanalı varsa at (BGRA -> BGR)
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # 16-bit vb. görüntüleri 8-bit'e çevir
        if img.dtype != np.uint8:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        self.original = img
        self.current = img.copy()
        self.path = path

    def save(self, path):
        ext = os.path.splitext(path)[1] or ".png"
        ok, buf = cv2.imencode(ext, self.current)
        if not ok:
            raise ValueError("Görüntü kaydedilemedi.")
        buf.tofile(path)

    def reset(self):
        self.current = self.original.copy()
