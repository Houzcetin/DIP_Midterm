"""Histogram analysis and luminance equalization."""

import cv2
import numpy as np

from ._validation import image


def equalize(img: np.ndarray) -> np.ndarray:
    """Equalize gray intensities or just the Y luminance channel in BGR-to-YCrCb."""
    image(img)
    if img.ndim == 2:
        return cv2.equalizeHist(img)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    ycrcb[:, :, 0] = cv2.equalizeHist(ycrcb[:, :, 0])
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)


def compute_hist(img: np.ndarray) -> dict[str, np.ndarray]:
    """Return 256 float counts per channel, keyed by 'gray' or BGR-order 'b', 'g', 'r'."""
    image(img)
    channels = {"gray": img} if img.ndim == 2 else dict(zip(("b", "g", "r"), cv2.split(img)))
    return {name: np.bincount(channel.ravel(), minlength=256).astype(np.float64)
            for name, channel in channels.items()}
