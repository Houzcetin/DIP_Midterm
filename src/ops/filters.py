"""Spatial smoothing and grayscale edge filters."""

import cv2
import numpy as np

from ._validation import choice, finite, image, odd_kernel, uint8
from .basics import to_grayscale


def box(img: np.ndarray, k: int) -> np.ndarray:
    """Average a k-by-k neighborhood; k is rounded up to an odd size >=1."""
    image(img)
    k = odd_kernel(k)
    return cv2.blur(img, (k, k))


def gaussian(img: np.ndarray, k: int, sigma: float = 0) -> np.ndarray:
    """Gaussian blur with odd k>=1 and sigma>=0; sigma=0 chooses it from k."""
    image(img)
    k = odd_kernel(k)
    sigma = max(0, finite(sigma, "sigma"))
    return cv2.GaussianBlur(img, (k, k), sigmaX=sigma)


def median(img: np.ndarray, k: int) -> np.ndarray:
    """Median filter with k rounded up to an odd size >=3."""
    image(img)
    return cv2.medianBlur(img, odd_kernel(k, minimum=3))


def laplacian(img: np.ndarray, k: int = 3) -> np.ndarray:
    """Absolute Laplacian, clipped to uint8; color input becomes gray; odd k is 1..31."""
    gray = to_grayscale(img)
    edges = cv2.Laplacian(gray, cv2.CV_64F, ksize=odd_kernel(k, maximum=31))
    return uint8(np.abs(edges))


def sobel(img: np.ndarray, direction: str, k: int = 3) -> np.ndarray:
    """Gray Sobel x/y absolute response or Euclidean magnitude ('both'); odd k is 1..31."""
    gray = to_grayscale(img)
    choice(direction, ("x", "y", "both"), "direction")
    k = odd_kernel(k, maximum=31)
    if direction == "x":
        return uint8(np.abs(cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)))
    if direction == "y":
        return uint8(np.abs(cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)))
    x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=k)
    y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=k)
    return uint8(np.hypot(x, y))
