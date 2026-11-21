"""Centered Fourier spectra and radial frequency filters for uint8 images."""

import numpy as np

from ._validation import choice, finite, image, uint8
from .basics import to_grayscale

KINDS = ("lowpass", "highpass", "bandpass", "bandstop")
SHAPES = ("ideal", "gaussian", "butterworth")


def _normalize(values, axes):
    shifted = values - values.min(axis=axes, keepdims=True)
    span = shifted.max(axis=axes, keepdims=True)
    # Ignore numerical FFT residue, notably from high-pass filtering a constant.
    scaled = np.divide(shifted, span, out=np.zeros_like(shifted), where=span > 1e-9)
    return uint8(scaled * 255)


def spectrum(img: np.ndarray, log: bool = True) -> np.ndarray:
    """Return a centered grayscale magnitude spectrum, optionally log-compressed."""
    gray = to_grayscale(img)
    magnitude = np.abs(np.fft.fftshift(np.fft.fft2(gray)))
    if log:
        magnitude = np.log1p(magnitude)
    return _normalize(magnitude, (0, 1))


def filter_mask(
    shape_hw: tuple[int, int], kind: str, shape: str, cutoff: float = 30.0,
    width: float = 10.0, order: int = 2,
) -> np.ndarray:
    """Return a centered mask in [0, 1], with band width measured across the ring.

    Cutoff is clamped from one bin to the largest represented radius (or one
    for a single pixel). For bands it sets the ring's center radius.
    """
    height, columns = shape_hw
    if height < 1 or columns < 1:
        raise ValueError("mask dimensions must be positive")
    choice(kind, KINDS, "kind")
    choice(shape, SHAPES, "shape")
    center_y, center_x = height // 2, columns // 2
    max_radius = max(1.0, np.hypot(center_y, center_x))
    cutoff = min(max_radius, max(1.0, finite(cutoff, "cutoff")))
    width = max(1.0, finite(width, "width"))
    order = max(1, int(finite(order, "order")))

    y, x = np.ogrid[-center_y:height - center_y, -center_x:columns - center_x]
    radius = np.hypot(y, x)
    if kind in ("bandpass", "bandstop"):
        ratio = np.abs(radius - cutoff) / (width / 2)
    else:
        ratio = radius / cutoff

    if shape == "ideal":
        mask = (ratio <= 1).astype(float)
    elif shape == "gaussian":
        mask = np.exp(-0.5 * ratio**2)
    else:
        with np.errstate(over="ignore"):
            mask = 1 / (1 + ratio**(2 * order))
    return 1 - mask if kind in ("highpass", "bandstop") else mask


def frequency_filter(
    img: np.ndarray, kind: str = "lowpass", shape: str = "ideal", cutoff: float = 30.0,
    width: float = 10.0, order: int = 2,
) -> np.ndarray:
    """Filter each channel independently; stretch high-pass magnitude and clip other output."""
    image(img)
    axes = (0, 1)
    mask = filter_mask(img.shape[:2], kind, shape, cutoff, width, order)
    mask = np.fft.ifftshift(mask)
    if img.ndim == 3:
        mask = mask[..., None]
    transformed = np.fft.fft2(img, axes=axes)
    transformed *= mask
    filtered = np.fft.ifft2(transformed, axes=axes).real
    if kind == "highpass":
        return _normalize(np.abs(filtered), axes)
    return uint8(filtered)
