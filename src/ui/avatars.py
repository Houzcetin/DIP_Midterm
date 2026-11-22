"""Pixel-art member figures shown for each theme.

The figures are transparent 384x640 PNGs in ui/assets/avatars/<theme id>.png.
Scaling always uses nearest-neighbour so the pixel art stays crisp.
"""

import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap

MEMBERS = ("mina", "esin", "zeynep", "lidya", "sueda", "hilal")
_ALPHA_THRESHOLD = 16


def asset_dir() -> Path:
    """Folder with the figure PNGs (also inside a PyInstaller onefile bundle)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / "ui" / "assets" / "avatars"


def _alpha(image: QImage) -> np.ndarray:
    """Alpha channel of an ARGB32 image as an (h, w) uint8 array."""
    ptr = image.constBits()
    data = np.frombuffer(ptr, np.uint8, count=image.sizeInBytes())
    rows = data.reshape(image.height(), image.bytesPerLine())[:, : image.width() * 4]
    return rows.reshape(image.height(), image.width(), 4)[:, :, 3]  # BGRA in memory


def _opaque_rect(image: QImage) -> QRect:
    """Bounding box of pixels with alpha above the threshold."""
    ys, xs = np.nonzero(_alpha(image) > _ALPHA_THRESHOLD)
    if xs.size == 0:
        return image.rect()
    return QRect(int(xs.min()), int(ys.min()), int(xs.max() - xs.min() + 1), int(ys.max() - ys.min() + 1))


@lru_cache(maxsize=None)
def figure(member: str) -> QImage:
    """Full figure cropped to its opaque bounding box (transparent background)."""
    image = QImage(str(asset_dir() / f"{member}.png"))
    if image.isNull():
        raise FileNotFoundError(f"missing avatar image for {member!r}")
    image = image.convertToFormat(QImage.Format.Format_ARGB32)
    return image.copy(_opaque_rect(image))


@lru_cache(maxsize=None)
def head(member: str) -> QImage:
    """Square crop around the head, used for small icons."""
    fig = figure(member)
    size = min(fig.width(), round(fig.height() * 0.16))
    # Centre on the opaque pixels of the top rows (the hair/face).
    cols = np.nonzero((_alpha(fig)[: max(1, size // 2)] > _ALPHA_THRESHOLD).any(axis=0))[0]
    cx = (int(cols.min()) + int(cols.max())) // 2 if cols.size else fig.width() // 2
    left = max(0, min(fig.width() - size, cx - size // 2))
    return fig.copy(QRect(left, 0, size, size))


def scaled(image: QImage, height: int) -> QImage:
    """Nearest-neighbour resize to the given height, keeping the aspect ratio."""
    return image.scaledToHeight(max(1, height), Qt.TransformationMode.FastTransformation)


def figure_pixmap(member: str, height: int) -> QPixmap:
    return QPixmap.fromImage(scaled(figure(member), height))


@lru_cache(maxsize=None)
def head_icon(member: str) -> QIcon:
    """Icon of the member's head at the common icon sizes."""
    face = head(member)
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        # Downscaling smooths to avoid dropped pixels; upscaling stays blocky.
        mode = (Qt.TransformationMode.SmoothTransformation if size < face.height()
                else Qt.TransformationMode.FastTransformation)
        icon.addPixmap(QPixmap.fromImage(face.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, mode)))
    return icon
