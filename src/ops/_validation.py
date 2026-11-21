"""Shared validation for gray or BGR uint8 image operations."""

import math

import numpy as np


def image(img: np.ndarray) -> np.ndarray:
    if not isinstance(img, np.ndarray) or img.dtype != np.uint8:
        raise TypeError("img must be a numpy uint8 array")
    if img.ndim not in (2, 3) or (img.ndim == 3 and img.shape[2] != 3):
        raise ValueError("img must be 2-D gray or 3-channel BGR")
    if not img.shape[0] or not img.shape[1]:
        raise ValueError("img must not be empty")
    return img


def finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def odd_kernel(k: int, minimum: int = 1, maximum: int | None = None) -> int:
    k = max(minimum, int(finite(k, "k")))
    if k % 2 == 0:
        k += 1
    return min(k, maximum) if maximum is not None else k


def choice(value: str, choices: tuple[str, ...], name: str) -> str:
    if value not in choices:
        raise ValueError(f"{name} must be one of {choices}")
    return value


def uint8(values: np.ndarray) -> np.ndarray:
    return np.clip(np.rint(values), 0, 255).astype(np.uint8)
