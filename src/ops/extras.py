"""Additional contrast, detail, noise, and artistic image operations."""

import cv2
import numpy as np

from ._validation import choice, finite, image, odd_kernel, uint8
from .basics import to_grayscale
from .filters import gaussian


def clahe(img: np.ndarray, clip: float = 2.0, tile: int = 8) -> np.ndarray:
    """Adaptive equalization with clip>0 and tile-by-tile grid; color uses LAB L only."""
    image(img)
    clip = max(0.01, finite(clip, "clip"))
    tile = max(1, int(finite(tile, "tile")))
    equalizer = cv2.createCLAHE(clipLimit=clip, tileGridSize=(tile, tile))
    if img.ndim == 2:
        return equalizer.apply(img)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    lab[:, :, 0] = equalizer.apply(lab[:, :, 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def unsharp(img: np.ndarray, k: int = 5, amount: float = 1.0) -> np.ndarray:
    """Sharpen by adding amount>=0 times the residual of a Gaussian blur with odd k>=1."""
    blurred = gaussian(img, k)
    amount = max(0, finite(amount, "amount"))
    return uint8(img.astype(np.float64) + amount * (img.astype(np.float64) - blurred))


def canny(img: np.ndarray, t1: float, t2: float) -> np.ndarray:
    """Return gray Canny edges; t1/t2 are sorted low/high thresholds clamped to 0..255."""
    gray = to_grayscale(img)
    low, high = sorted(np.clip([finite(t1, "t1"), finite(t2, "t2")], 0, 255))
    return cv2.Canny(gray, float(low), float(high))


def add_noise(img: np.ndarray, kind: str, amount: float, seed: int | None = None) -> np.ndarray:
    """Add salt_pepper (pixel fraction) or gaussian (std/255) noise; amount is 0..1.

    A seed gives repeatable local randomness without changing numpy's global RNG.
    """
    image(img)
    choice(kind, ("salt_pepper", "gaussian"), "kind")
    amount = float(np.clip(finite(amount, "amount"), 0, 1))
    rng = np.random.default_rng(seed)
    if kind == "gaussian":
        return uint8(img.astype(np.float64) + rng.normal(0, amount * 255, img.shape))
    result = img.copy()
    mask = rng.random(img.shape[:2])
    result[mask < amount / 2] = 0
    result[mask >= 1 - amount / 2] = 255
    return result


def sepia(img: np.ndarray) -> np.ndarray:
    """Apply classic sepia coefficients; gray input is promoted to BGR and output is BGR."""
    image(img)
    bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img
    matrix = np.array([[0.131, 0.534, 0.272], [0.168, 0.686, 0.349],
                       [0.189, 0.769, 0.393]], dtype=np.float64)
    return uint8(cv2.transform(bgr.astype(np.float64), matrix))


def bilateral(img: np.ndarray, d: int = 9, sigma_color: float = 75, sigma_space: float = 75) -> np.ndarray:
    """Edge-preserving blur with odd diameter d>=1 and nonnegative color/spatial sigmas."""
    image(img)
    d = odd_kernel(d)
    sigma_color = max(0, finite(sigma_color, "sigma_color"))
    sigma_space = max(0, finite(sigma_space, "sigma_space"))
    return cv2.bilateralFilter(img, d, sigma_color, sigma_space)
