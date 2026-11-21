"""Basic, lossless image transformations."""

import cv2
import numpy as np

from ._validation import choice, finite, image


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert BGR to gray; an already gray image is returned as a copy."""
    image(img)
    return img.copy() if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def flip(img: np.ndarray, mode: str) -> np.ndarray:
    """Flip horizontally ('h'), vertically ('v'), or along both axes ('both')."""
    image(img)
    choice(mode, ("h", "v", "both"), "mode")
    return cv2.flip(img, {"h": 1, "v": 0, "both": -1}[mode])


def rotate90(img: np.ndarray, k: int) -> np.ndarray:
    """Rotate k quarter-turns clockwise, modulo 4; k=-1 or 3 is counterclockwise."""
    image(img)
    turns = int(finite(k, "k")) % 4
    return np.rot90(img, -turns).copy()
