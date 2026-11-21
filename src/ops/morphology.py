"""Binary thresholding and per-channel gray/BGR morphology."""

import cv2
import numpy as np

from ._validation import choice, finite, image, odd_kernel
from .basics import to_grayscale


def threshold(img: np.ndarray, method: str, t: float = 127, invert: bool = False) -> np.ndarray:
    """Return binary gray via global t (clamped to 0..255) or Otsu; invert swaps black/white."""
    gray = to_grayscale(img)
    choice(method, ("global", "otsu"), "method")
    t = float(np.clip(finite(t, "t"), 0, 255))
    mode = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    if method == "otsu":
        mode |= cv2.THRESH_OTSU
    return cv2.threshold(gray, t, 255, mode)[1]


def _morph(img, operation, k, shape, iterations):
    image(img)
    choice(shape, ("rect", "ellipse", "cross"), "shape")
    k = odd_kernel(k)
    iterations = max(1, int(finite(iterations, "iterations")))
    shapes = {"rect": cv2.MORPH_RECT, "ellipse": cv2.MORPH_ELLIPSE, "cross": cv2.MORPH_CROSS}
    kernel = cv2.getStructuringElement(shapes[shape], (k, k))
    return cv2.morphologyEx(img, operation, kernel, iterations=iterations)


def erode(img: np.ndarray, k: int = 3, shape: str = "rect", iterations: int = 1) -> np.ndarray:
    """Shrink bright regions; odd k>=1, shape=rect/ellipse/cross, iterations>=1."""
    return _morph(img, cv2.MORPH_ERODE, k, shape, iterations)


def dilate(img: np.ndarray, k: int = 3, shape: str = "rect", iterations: int = 1) -> np.ndarray:
    """Grow bright regions; odd k>=1, shape=rect/ellipse/cross, iterations>=1."""
    return _morph(img, cv2.MORPH_DILATE, k, shape, iterations)


def opening(img: np.ndarray, k: int = 3, shape: str = "rect", iterations: int = 1) -> np.ndarray:
    """Erode then dilate to remove bright specks; odd k>=1, shape, iterations>=1."""
    return _morph(img, cv2.MORPH_OPEN, k, shape, iterations)


def closing(img: np.ndarray, k: int = 3, shape: str = "rect", iterations: int = 1) -> np.ndarray:
    """Dilate then erode to fill dark holes; odd k>=1, shape, iterations>=1."""
    return _morph(img, cv2.MORPH_CLOSE, k, shape, iterations)
