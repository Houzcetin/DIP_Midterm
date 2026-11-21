"""Pointwise intensity transforms."""

import cv2
import numpy as np

from ._validation import finite, image, uint8


def contrast_stretch(img: np.ndarray, low_pct: float = 2, high_pct: float = 98) -> np.ndarray:
    """Stretch low_pct..high_pct percentiles to 0..255 independently per channel.

    Percentiles are clamped to 0..100 and must be increasing; constant channels stay unchanged.
    """
    image(img)
    low_pct = np.clip(finite(low_pct, "low_pct"), 0, 100)
    high_pct = np.clip(finite(high_pct, "high_pct"), 0, 100)
    if low_pct >= high_pct:
        raise ValueError("low_pct must be less than high_pct")
    low, high = np.percentile(img, (low_pct, high_pct), axis=(0, 1))
    span = high - low
    stretched = (img.astype(np.float64) - low) * 255 / np.where(span > 0, span, 1)
    return uint8(np.where(span > 0, stretched, img))


def gamma(img: np.ndarray, g: float) -> np.ndarray:
    """Apply 255*(intensity/255)**g with a 256-entry LUT; g>1 darkens, 0<g<1 brightens."""
    image(img)
    g = finite(g, "g")
    if g <= 0:
        raise ValueError("g must be positive")
    lut = uint8(255 * (np.arange(256, dtype=np.float64) / 255) ** g)
    return cv2.LUT(img, lut)


def negative(img: np.ndarray) -> np.ndarray:
    """Invert every gray or BGR intensity with 255-intensity."""
    image(img)
    return cv2.bitwise_not(img)
