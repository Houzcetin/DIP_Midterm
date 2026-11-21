"""Configure the test import root and headless Qt platform."""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def bgr_png(tmp_path):
    image = np.random.default_rng(4360).integers(0, 256, (48, 64, 3), dtype=np.uint8)
    folder = tmp_path / "görsel"
    folder.mkdir()
    path = folder / "örnek.png"
    ok, encoded = cv2.imencode(".png", image)
    assert ok
    encoded.tofile(path)
    return path, image
