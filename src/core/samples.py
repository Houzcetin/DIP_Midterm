"""Deterministic BGR sample images for exploring processing operations."""

from collections.abc import Callable

import cv2
import numpy as np

from ops.extras import add_noise

_HEIGHT, _WIDTH = 480, 640
_FONT = cv2.FONT_HERSHEY_SIMPLEX


def shapes() -> np.ndarray:
    """Generate the original colorful shapes sample."""
    horizontal = np.linspace(0, 255, _WIDTH, dtype=np.uint8)
    vertical = np.linspace(20, 230, _HEIGHT, dtype=np.uint8)[:, None]
    img = np.empty((_HEIGHT, _WIDTH, 3), dtype=np.uint8)
    img[..., 0] = horizontal
    img[..., 1] = vertical
    img[..., 2] = horizontal[::-1]

    cv2.rectangle(img, (32, 28), (608, 160), (30, 30, 30), -1)
    cv2.putText(img, "COMP 4360", (53, 90), _FONT, 1.5, (245, 245, 245), 3, cv2.LINE_AA)
    cv2.putText(img, "Image Processing Sample", (55, 132), _FONT,
                0.8, (200, 216, 235), 2, cv2.LINE_AA)
    cv2.circle(img, (133, 299), 84, (240, 219, 82), -1, cv2.LINE_AA)
    cv2.circle(img, (133, 299), 45, (45, 45, 45), 3, cv2.LINE_AA)
    cv2.rectangle(img, (238, 225), (396, 382), (110, 78, 210), -1, cv2.LINE_AA)
    cv2.fillConvexPoly(img, np.array([(426, 383), (517, 215), (608, 383)], dtype=np.int32),
                       (238, 238, 238), cv2.LINE_AA)
    return img


def _landscape() -> np.ndarray:
    sky = np.linspace((170, 117, 69), (237, 215, 179), _HEIGHT, dtype=np.uint8)
    img = np.repeat(sky[:, None, :], _WIDTH, axis=1)
    cv2.circle(img, (495, 151), 45, (145, 223, 248), -1, cv2.LINE_AA)
    x = np.arange(_WIDTH)
    for level, amplitude, phase, color in (
        (286, 42, 0.4, (129, 131, 103)),
        (350, 52, 2.3, (88, 119, 71)),
        (419, 36, 3.5, (56, 92, 45)),
    ):
        ridge = level + amplitude * (np.sin(x / 104 + phase) + 0.28 * np.sin(x / 47 - phase))
        points = np.column_stack((x, ridge))
        polygon = np.vstack((points, [(_WIDTH - 1, _HEIGHT - 1), (0, _HEIGHT - 1)]))
        cv2.fillPoly(img, [polygon.astype(np.int32)], color, cv2.LINE_AA)
    return img


def noisy() -> np.ndarray:
    """Add 6% salt-and-pepper noise to a smooth landscape."""
    return add_noise(_landscape(), "salt_pepper", 0.06, seed=4360)


def low_contrast() -> np.ndarray:
    """Compress the landscape into a slightly dark, narrow intensity range."""
    return np.rint(90 + _landscape() * (60 / 255)).astype(np.uint8)


def document() -> np.ndarray:
    """Generate a portrait document with shadow, uneven light, and mild paper noise."""
    height, width = 800, 600
    paper = np.full((height, width), 255, dtype=np.uint8)
    cv2.putText(paper, "FIELD NOTES", (46, 97), _FONT, 1.45, 18, 3, cv2.LINE_AA)
    for row, line in enumerate((
        "Site: Cedar Ridge Observatory",
        "Morning survey, 14 October",
        "The sky cleared just after sunrise.",
        "We recorded the light at three stations.",
        "Station B remained in partial shadow.",
        "Readings are listed below in lux.",
    )):
        cv2.putText(paper, line, (48, 155 + 43 * row), _FONT, 0.72, 20, 2, cv2.LINE_AA)

    cv2.rectangle(paper, (47, 418), (551, 669), 25, 2)
    cv2.line(paper, (324, 418), (324, 669), 25, 2)
    for row, (label, value) in enumerate((
        ("Station", "Light (lx)"), ("A", "860"), ("B", "290"), ("C", "725"),
    )):
        y = 418 + 62 * row
        if row:
            cv2.line(paper, (47, y), (551, y), 25, 2)
        cv2.putText(paper, label, (71, y + 41), _FONT, 0.8, 20, 2, cv2.LINE_AA)
        cv2.putText(paper, value, (348, y + 41), _FONT, 0.8, 20, 2, cv2.LINE_AA)
    cv2.putText(paper, "End of survey", (48, 744), _FONT, 0.65, 20, 2, cv2.LINE_AA)

    y, x = np.ogrid[0:height, 0:width]
    light = 0.32 + 0.66 * np.exp(-((x - 440) / 375)**2 - ((y - 230) / 530)**2)
    rng = np.random.default_rng(4360)
    shaded = np.clip(np.rint(paper * light + rng.normal(0, 3, paper.shape)), 0, 255)
    return cv2.cvtColor(shaded.astype(np.uint8), cv2.COLOR_GRAY2BGR)


def binary_holes() -> np.ndarray:
    """Draw binary shapes with pinholes and isolated foreground specks."""
    img = np.zeros((_HEIGHT, _WIDTH), dtype=np.uint8)
    cv2.circle(img, (157, 123), 74, 255, -1)
    cv2.ellipse(img, (463, 129), (110, 64), -21, 0, 360, 255, -1)
    cv2.putText(img, "DIP", (113, 409), _FONT, 5.5, 255, 30)

    rng = np.random.default_rng(4360)
    for x, y in rng.integers((4, 4), (_WIDTH - 4, _HEIGHT - 4), (1100, 2)):
        if img[y, x] == 255:
            cv2.circle(img, (int(x), int(y)), int(rng.integers(1, 3)), 0, -1)
        elif rng.random() < 0.24:
            img[y, x] = 255
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def grid() -> np.ndarray:
    """Draw a numbered checkerboard grid and a circle for geometric transforms."""
    y, x = np.ogrid[0:_HEIGHT, 0:_WIDTH]
    checks = ((x // 80 + y // 80) % 2 * 108 + 95).astype(np.uint8)
    img = cv2.cvtColor(checks, cv2.COLOR_GRAY2BGR)
    for x in range(0, _WIDTH, 80):
        cv2.line(img, (x, 0), (x, _HEIGHT - 1), (63, 133, 215), 2)
        cv2.putText(img, str(x), (x + 8, 25), _FONT, 0.55, (26, 42, 73), 2, cv2.LINE_AA)
    for y in range(80, _HEIGHT, 80):
        cv2.line(img, (0, y), (_WIDTH - 1, y), (63, 133, 215), 2)
        cv2.putText(img, str(y), (8, y + 24), _FONT, 0.55, (26, 42, 73), 2, cv2.LINE_AA)
    cv2.circle(img, (_WIDTH // 2, _HEIGHT // 2), 141, (76, 41, 157), 4, cv2.LINE_AA)
    return img


def edges() -> np.ndarray:
    """Generate sharp circles and spokes alongside a sinusoidal zone plate."""
    img = np.full((_HEIGHT, _WIDTH), 29, dtype=np.uint8)
    center = (165, 257)
    for radius in range(27, 133, 21):
        cv2.circle(img, center, radius, 239, 2, cv2.LINE_AA)
    for angle in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        direction = np.array([np.cos(angle), np.sin(angle)])
        start = tuple(np.rint(center + 18 * direction).astype(int))
        end = tuple(np.rint(center + 132 * direction).astype(int))
        cv2.line(img, start, end, 175, 1, cv2.LINE_AA)

    y, x = np.ogrid[-124:125, -124:125]
    r_squared = x**2 + y**2
    plate = np.rint(128 + 115 * np.sin(0.012 * r_squared)).astype(np.uint8)
    disk = r_squared <= 124**2
    region = img[133:382, 351:600]
    region[disk] = plate[disk]
    cv2.putText(img, "EDGES AND FREQUENCIES", (31, 74), _FONT, 1.12, 240, 2, cv2.LINE_AA)
    return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)


def periodic_noise() -> np.ndarray:
    """Add a sinusoid with a pair of spectral peaks about 31 bins from DC."""
    y, x = np.ogrid[0:_HEIGHT, 0:_WIDTH]
    stripes = 34 * np.sin(2 * np.pi * (30 * x / _WIDTH + 8 * y / _HEIGHT))
    return np.clip(np.rint(_landscape() + stripes[..., None]), 0, 255).astype(np.uint8)


SAMPLES: dict[str, tuple[str, str, Callable[[], np.ndarray]]] = {
    "shapes": ("Colorful shapes", "Try Grayscale, Negative, or Histogram equalization.", shapes),
    "noisy": ("Noisy (salt & pepper)", "Compare Median with Box or Gaussian blur.", noisy),
    "low_contrast": ("Low-contrast landscape",
                     "Try Contrast stretch, Gamma, Histogram equalization, or CLAHE.", low_contrast),
    "document": ("Unevenly lit document", "Compare Global and Otsu thresholds, then try morphology.", document),
    "binary_holes": ("Binary shapes with holes", "Try Opening, Closing, Erode, and Dilate.", binary_holes),
    "grid": ("Checkerboard grid", "Try Rotate, Scale, Shear, or Translate.", grid),
    "edges": ("Edges and zone plate", "Try Sobel, Laplacian, Canny, or FFT spectrum.", edges),
    "periodic_noise": ("Periodic stripe noise",
                       "Try FFT spectrum, then Ideal Band-stop with cutoff 31 and width 4.", periodic_noise),
}
