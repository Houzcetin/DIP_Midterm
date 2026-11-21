"""Affine transforms with black fill outside the source image."""

import cv2
import numpy as np

from ._validation import finite, image


def _warp(img, matrix, expand=False, border=0):
    h, w = img.shape[:2]
    matrix = np.asarray(matrix, dtype=np.float64).copy()
    if expand:
        # Transform outer pixel edges, then center them in the expanded canvas.
        corners = np.array([[-0.5, -0.5, 1], [w - 0.5, -0.5, 1],
                            [-0.5, h - 0.5, 1], [w - 0.5, h - 0.5, 1]])
        transformed = corners @ matrix.T
        lower, upper = transformed.min(axis=0), transformed.max(axis=0)
        w, h = np.maximum(1, np.ceil(upper - lower - 1e-10)).astype(int)
        matrix[:, 2] += (np.array([w, h]) - 1) / 2 - (lower + upper) / 2
    if np.isscalar(border):
        value = int(np.clip(finite(border, "border"), 0, 255))
        border = (value, value, value)
    else:
        if len(border) != 3:
            raise ValueError("border must be a gray value or a BGR triple")
        border = tuple(int(np.clip(finite(v, "border"), 0, 255)) for v in border)
    return cv2.warpAffine(img, matrix, (int(w), int(h)), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def rotate(img: np.ndarray, angle_deg: float, expand: bool = True, border=0) -> np.ndarray:
    """Rotate counterclockwise by angle_deg about the center; expand avoids cropping.

    border is a fill intensity or BGR triple (black by default).
    """
    image(img)
    h, w = img.shape[:2]
    matrix = cv2.getRotationMatrix2D(((w - 1) / 2, (h - 1) / 2),
                                     finite(angle_deg, "angle_deg") % 360, 1)
    return _warp(img, matrix, expand, border)


def scale(img: np.ndarray, sx: float, sy: float, interp="linear") -> np.ndarray:
    """Resize by positive horizontal sx and vertical sy factors (at least one pixel).

    interp is nearest, linear, cubic, area, lanczos, or an OpenCV interpolation code.
    """
    image(img)
    sx, sy = finite(sx, "sx"), finite(sy, "sy")
    if sx <= 0 or sy <= 0:
        raise ValueError("sx and sy must be positive")
    modes = {"nearest": cv2.INTER_NEAREST, "linear": cv2.INTER_LINEAR,
             "cubic": cv2.INTER_CUBIC, "area": cv2.INTER_AREA,
             "lanczos": cv2.INTER_LANCZOS4}
    if isinstance(interp, str):
        if interp not in modes:
            raise ValueError(f"interp must be one of {tuple(modes)}")
        interp = modes[interp]
    elif interp not in modes.values():
        raise ValueError("unsupported OpenCV interpolation code")
    h, w = img.shape[:2]
    return cv2.resize(img, (max(1, round(w * sx)), max(1, round(h * sy))),
                      interpolation=interp)


def translate(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Shift by dx pixels right and dy pixels down, keeping the original canvas."""
    image(img)
    return _warp(img, [[1, 0, finite(dx, "dx")], [0, 1, finite(dy, "dy")]])


def shear(img: np.ndarray, shx: float, shy: float, expand: bool = True) -> np.ndarray:
    """Shear x by shx*y and y by shy*x; expand preserves the transformed bounds."""
    image(img)
    shx, shy = finite(shx, "shx"), finite(shy, "shy")
    if abs(1 - shx * shy) < 1e-12:
        raise ValueError("shx * shy must not equal 1 (singular transform)")
    return _warp(img, [[1, shx, 0], [shy, 1, 0]], expand)
