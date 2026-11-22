import os
import cv2
import numpy as np


class ImageState:
    """Store the original image and up to 30 history steps."""

    MAX_HISTORY = 30

    def __init__(self):
        self.original = None
        self.path = None
        self._history: list[tuple[str, np.ndarray, dict]] = []
        self._index = -1

    @property
    def current(self):
        return self._history[self._index][1] if self._history else None

    @property
    def index(self):
        return self._index

    def has_image(self):
        return self.original is not None

    def load(self, path):
        # cv2.imread Türkçe karakterli yolları (ör. "Masaüstü") okuyamaz,
        # bu yüzden dosyayı byte olarak okuyup imdecode ile çözüyoruz.
        data = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Could not read image: {path}")
        self.load_array(img, path)

    def load_array(self, img, name):
        """Start a new document from a gray, BGR, or BGRA array."""
        if not img.size or not (img.ndim == 2 or (img.ndim == 3 and img.shape[2] in (3, 4))):
            raise ValueError("Expected a non-empty grayscale, BGR, or BGRA image.")
        # Alpha kanalı varsa at (BGRA -> BGR)
        if img.ndim == 3 and img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        # 16-bit vb. görüntüleri 8-bit'e çevir
        if img.dtype != np.uint8:
            img = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        self._start_history(img.copy())
        self.path = name

    def save(self, path):
        ext = os.path.splitext(path)[1] or ".png"
        ok, buf = cv2.imencode(ext, self.current)
        if not ok:
            raise ValueError("Could not encode image.")
        buf.tofile(path)

    def reset(self):
        if self.has_image():
            self.apply("Reset", self.original)

    def apply(self, label, img, *, params=None):
        """Append a snapshot with its operation parameters and discard redo steps."""
        if not self.has_image():
            raise ValueError("Load an image before applying a result.")
        step = (label, img.copy(), dict(params or {}))
        del self._history[self._index + 1:]
        self._history.append(step)
        if len(self._history) > self.MAX_HISTORY:
            del self._history[1]
        self._index = len(self._history) - 1

    def can_undo(self):
        return self._index > 0

    def can_redo(self):
        return self._index < len(self._history) - 1

    def undo(self):
        self.goto(self._index - 1)

    def redo(self):
        self.goto(self._index + 1)

    def goto(self, index):
        if 0 <= index < len(self._history):
            self._index = index

    @staticmethod
    def _format_label(label, params):
        summary = ", ".join(f"{key}={value}" for key, value in params.items())
        return f"{label} ({summary})" if summary else label

    def history_labels(self, format_label=None):
        format_label = format_label or self._format_label
        return [format_label(label, params) for label, _, params in self._history]

    def set_result_as_original(self):
        if self.has_image():
            self._start_history(self.current)

    def _start_history(self, img):
        self.original = img
        self._history = [("Original", img, {})]
        self._index = 0
