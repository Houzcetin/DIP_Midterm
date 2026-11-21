import os
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def configure_appearance(app):
    """Apply the desktop theme and a generated application icon."""
    app.setStyle("Fusion")
    roles = QPalette.ColorRole
    palette = QPalette()
    for role, color in {
        roles.Window: "#25282d",
        roles.WindowText: "#e1e6ed",
        roles.Base: "#1e1e1e",
        roles.AlternateBase: "#2a2e35",
        roles.Text: "#e1e6ed",
        roles.Button: "#30363e",
        roles.ButtonText: "#e1e6ed",
        roles.ToolTipBase: "#333b47",
        roles.ToolTipText: "#f0f4f9",
        roles.Light: "#4b5562",
        roles.Mid: "#353c46",
        roles.Dark: "#1c2025",
        roles.Shadow: "#151719",
        roles.Highlight: "#3469a6",
        roles.HighlightedText: "#ffffff",
        roles.Link: "#81b7ff",
        roles.PlaceholderText: "#a0aab7",
    }.items():
        palette.setColor(role, QColor(color))
    for role in (roles.WindowText, roles.Text, roles.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#87919e"))
    app.setPalette(palette)
    app.setStyleSheet("""
        QDockWidget::title {
            background: #2e343c;
            padding-left: 8px;
        }
        QGroupBox {
            border: 1px solid #3a414a;
            border-radius: 5px;
            margin-top: 0.65em;
            padding-top: 0.35em;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: #e1e6ed;
        }
    """)

    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#3469a6"))
    painter.drawRoundedRect(QRectF(2, 2, 60, 60), 12, 12)
    painter.setPen(Qt.GlobalColor.white)
    painter.setFont(QFont("Sans Serif", 16, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "DIP")
    painter.end()
    app.setWindowIcon(QIcon(pixmap))


def run_selftest(app, out_dir):
    """Exercise every operation headlessly and write a report + screenshot.

    Used to verify the frozen exe: `DIP_Midterm.exe --selftest <dir>`.
    A windowed exe has no console, so results go to files in out_dir.
    """
    import traceback
    from pathlib import Path
    from PySide6.QtCore import QSettings
    from ops.registry import OPERATIONS

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = out / "selftest.txt"
    try:
        settings = QSettings(str(out / "selftest.ini"), QSettings.Format.IniFormat)
        window = MainWindow(settings)
        window.resize(1500, 850)
        window.show()
        window.open_sample_image()
        for op in OPERATIONS:
            window.apply_operation(op.id, {p.name: p.default for p in op.params})
            window.undo()
        window.apply_operation("gaussian", {"k": 5, "sigma": 0.0})
        window.apply_operation("equalize", {})
        app.processEvents()
        window.histogram_view.canvas.draw()
        window.grab().save(str(out / "selftest.png"))
        report.write_text(f"OK {len(OPERATIONS)} operations, "
                          f"history={len(window.state.history_labels())}\n", encoding="utf-8")
        return 0
    except Exception:
        report.write_text("FAIL\n" + traceback.format_exc(), encoding="utf-8")
        return 1


def main():
    if "--selftest" in sys.argv:
        # Render offscreen so the self-test never pops up on the desktop.
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        app = QApplication(sys.argv)
        configure_appearance(app)
        index = sys.argv.index("--selftest")
        out_dir = sys.argv[index + 1] if index + 1 < len(sys.argv) else "selftest_out"
        sys.exit(run_selftest(app, out_dir))

    app = QApplication(sys.argv)
    configure_appearance(app)
    window = MainWindow()
    # The default 1400x800 does not fit small or scaled screens (e.g. 1536x864 at 125%).
    available = app.primaryScreen().availableGeometry()
    if available.width() < 1500 or available.height() < 900:
        window.showMaximized()
    else:
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
