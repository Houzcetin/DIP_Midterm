import os
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from ui import avatars
from ui.main_window import MainWindow
from ui.themes import DEFAULT_THEME, THEMES, apply_theme, get_theme


def configure_appearance(app, theme_id=None):
    """Start Fusion with the saved theme or the default appearance."""
    app.setStyle("Fusion")
    apply_theme(app, get_theme(theme_id))


def run_selftest(app, out_dir):
    """Exercise operations, themes, and languages headlessly and write a report and screenshot.

    Used to verify the frozen exe: `DIP_Midterm.exe --selftest <dir>`.
    A windowed exe has no console, so results go to files in out_dir.
    """
    import traceback
    from pathlib import Path
    from ops.extras import add_noise
    from ops.intensity import gamma
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
        for theme_id in THEMES:
            window.set_theme(theme_id)
            app.processEvents()
        for language in ("tr", "en"):
            window.set_language(language)
            app.processEvents()
        # Fails if the figure PNGs were not bundled into the exe.
        avatar_count = sum(not avatars.figure(member).isNull() for member in avatars.MEMBERS)
        window.set_theme(DEFAULT_THEME)
        degraded = add_noise(gamma(window.state.current, 2.5), "gaussian", 0.06, seed=4360)
        window.state.load_array(degraded, "selftest_degraded.png")
        window.refresh()
        window.auto_enhance()
        auto_steps = window.state.index
        if not auto_steps:
            raise RuntimeError("Auto Enhance did not apply any steps to the degraded sample.")
        window.auto_report_dialog.close()
        window.open_sample_image()
        window.apply_operation("gaussian", {"k": 5, "sigma": 0.0})
        window.apply_operation("equalize", {})
        app.processEvents()
        window.histogram_view.canvas.draw()
        window.grab().save(str(out / "selftest.png"))
        report.write_text(f"OK {len(OPERATIONS)} operations, themes={len(THEMES)}, languages=2, "
                          f"avatars={avatar_count}, history={len(window.state.history_labels())}, "
                          f"auto_steps={auto_steps}\n",
                          encoding="utf-8")
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
    settings = QSettings("DIPMidterm", "App")
    configure_appearance(app, settings.value("theme"))
    window = MainWindow(settings)
    # The default 1400x800 does not fit small or scaled screens (e.g. 1536x864 at 125%).
    available = app.primaryScreen().availableGeometry()
    if available.width() < 1500 or available.height() < 900:
        window.showMaximized()
    else:
        window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
