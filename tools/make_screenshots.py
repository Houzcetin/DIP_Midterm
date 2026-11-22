"""Render the screenshots used by README.md into media/.

Run with: .venv\\Scripts\\python.exe tools\\make_screenshots.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
from PySide6.QtCore import QRect, QSettings, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QApplication

from core.samples import SAMPLES
from main import configure_appearance
from ui import avatars
from ui.main_window import MainWindow
from ui.themes import THEMES

MEDIA = ROOT / "media"


def save(widget_or_image, name):
    image = widget_or_image if isinstance(widget_or_image, QImage) else widget_or_image.grab().toImage()
    if not image.save(str(MEDIA / name), "PNG"):
        raise RuntimeError(f"Could not save {name}")


def damaged_sample():
    """Darken the shapes sample and sprinkle salt-and-pepper noise over it."""
    shapes = SAMPLES["shapes"][2]()
    mask = np.random.default_rng(1).random(shapes.shape[:2])
    damaged = (shapes * 0.35).astype(np.uint8)
    damaged[mask < 0.03], damaged[mask > 0.97] = 0, 255
    return damaged


def theme_strip():
    """All six member figures side by side with their theme names."""
    height, cell, label = 360, 230, 56
    strip = QImage(cell * len(THEMES), height + label, QImage.Format.Format_ARGB32)
    strip.fill(QColor("#1e2127"))
    with QPainter(strip) as painter:
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        font = QFont("Segoe UI")
        font.setPixelSize(20)
        font.setBold(True)
        for index, theme in enumerate(THEMES.values()):
            figure = avatars.scaled(avatars.figure(theme.id), height - 24)
            x = index * cell + (cell - figure.width()) // 2
            painter.drawImage(x, 12, figure)
            painter.setFont(font)
            painter.setPen(QColor(theme.accent))
            painter.drawText(QRect(index * cell, height, cell, label // 2),
                             Qt.AlignmentFlag.AlignCenter, theme.member)
            small = QFont(font)
            small.setBold(False)
            small.setPixelSize(16)
            painter.setFont(small)
            painter.setPen(QColor("#c3cad4"))
            painter.drawText(QRect(index * cell, height + label // 2, cell, label // 2),
                             Qt.AlignmentFlag.AlignCenter, theme.color_name)
    return strip


def main():
    MEDIA.mkdir(exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    configure_appearance(app, "zeynep")
    with tempfile.TemporaryDirectory() as folder:
        window = MainWindow(QSettings(str(Path(folder) / "shots.ini"), QSettings.Format.IniFormat))
        window.resize(1500, 850)
        window.set_theme("zeynep")
        window.set_language("en")
        window.show()
        app.processEvents()
        save(window, "empty_state.png")

        window.open_sample_image()
        window.apply_operation("gaussian", {"k": 5, "sigma": 0.0})
        window.apply_operation("equalize", {})
        window.wipe_action.setChecked(True)
        app.processEvents()
        window.histogram_view.canvas.draw()
        save(window, "main_window.png")
        window.wipe_action.setChecked(False)

        window.set_theme("hilal")
        window.state.load_array(damaged_sample(), "damaged.png")
        window.refresh()
        window.auto_enhance()
        app.processEvents()
        window.histogram_view.canvas.draw()
        save(window, "auto_enhance.png")
        save(window.auto_report_dialog, "auto_report.png")

        window.set_theme("sueda")
        window.set_language("tr")
        app.processEvents()
        window.histogram_view.canvas.draw()
        save(window, "turkish_ui.png")
        window.auto_report_dialog.close()
        window.close()
    save(theme_strip(), "themes.png")
    print(f"Saved screenshots to {MEDIA}")


if __name__ == "__main__":
    main()
