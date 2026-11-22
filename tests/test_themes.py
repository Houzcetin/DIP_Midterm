"""Theme contrast, menu persistence, and live plot updates."""

import pytest
from matplotlib.colors import to_rgba
from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest

from ui.main_window import MainWindow
from ui.themes import DEFAULT_THEME, THEMES, build_palette, build_stylesheet, get_theme


def relative_luminance(color):
    channels = [value / 255 for value in bytes.fromhex(color.removeprefix("#"))]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    r, g, b = linear
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(first, second):
    dark, light = sorted(map(relative_luminance, (first, second)))
    return (light + 0.05) / (dark + 0.05)


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "themes.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def create_window(qapp):
    palette, stylesheet, icon = qapp.palette(), qapp.styleSheet(), qapp.windowIcon()
    windows = []

    def create(settings):
        window = MainWindow(settings)
        windows.append(window)
        return window

    yield create
    for window in windows:
        window.close()
        window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.setStyleSheet(stylesheet)
    qapp.setPalette(palette)
    qapp.setWindowIcon(icon)


def theme_actions(window):
    view_menu = next(action.menu() for action in window.menuBar().actions() if action.text() == "&View")
    theme_menu = next(action.menu() for action in view_menu.actions() if action.text() == "Theme")
    return theme_menu.actions()


def test_registry_order_labels_and_default():
    assert list(THEMES) == ["mina", "esin", "zeynep", "lidya", "sueda", "hilal"]
    assert [theme.id for theme in THEMES.values()] == list(THEMES)
    assert [theme.label for theme in THEMES.values()] == [
        "Mina — Red", "Esin — Yellow", "Zeynep Sude — Blue",
        "Lidya — Pink", "Sueda — Green", "Hilal — Purple",
    ]
    assert DEFAULT_THEME == "zeynep"
    assert get_theme(None) is get_theme("unknown") is THEMES[DEFAULT_THEME]


@pytest.mark.parametrize("theme_id", THEMES)
def test_theme_contrast_and_qt_colors(theme_id):
    theme = get_theme(theme_id)
    assert contrast_ratio(theme.on_accent, theme.accent) >= 4.5
    assert contrast_ratio(theme.text, theme.window) >= 7
    assert contrast_ratio(theme.text, theme.base) >= 7
    palette = build_palette(theme)
    assert palette.color(QPalette.ColorRole.Highlight) == QColor(theme.accent)
    assert palette.color(QPalette.ColorRole.HighlightedText) == QColor(theme.on_accent)
    assert palette.color(QPalette.ColorRole.Link) == QColor(theme.accent)
    assert theme.accent in build_stylesheet(theme)


def test_theme_menu_is_exclusive_and_selection_persists(create_window, settings, qapp):
    window = create_window(settings)
    actions = theme_actions(window)
    assert len(actions) == 6
    assert [action.text() for action in actions] == [theme.label for theme in THEMES.values()]
    assert all(action.isCheckable() and not action.icon().isNull() for action in actions)
    group = actions[0].actionGroup()
    assert group.isExclusive() and group.actions() == actions
    assert group.checkedAction().data() == DEFAULT_THEME

    emitted = []
    window.themeChanged.connect(emitted.append)
    actions[0].trigger()
    assert group.checkedAction() == actions[0]
    assert settings.value("theme") == "mina"
    assert emitted == [THEMES["mina"]]
    assert qapp.palette().color(QPalette.ColorRole.Highlight) == QColor(THEMES["mina"].accent)

    settings.sync()
    stored_settings = QSettings(settings.fileName(), QSettings.Format.IniFormat)
    reopened = create_window(stored_settings)
    assert [action.data() for action in theme_actions(reopened) if action.isChecked()] == ["mina"]
    assert reopened.histogram_view.figure.get_facecolor() == to_rgba(THEMES["mina"].window)


def test_invalid_saved_theme_checks_default(create_window, settings):
    settings.setValue("theme", "unknown")
    window = create_window(settings)
    assert [action.data() for action in theme_actions(window) if action.isChecked()] == [DEFAULT_THEME]


def test_open_plots_follow_theme_and_frequency_keeps_it_when_redrawn(create_window, settings, bgr_png):
    window = create_window(settings)
    window.show_histogram_window()
    window.show_frequency_inspector()
    dock = window.histogram_view
    dialog = window._dialog_histogram
    frequency = window._frequency_dialog
    default = get_theme(None)
    theme = get_theme("esin")

    for view in (dock, dialog, frequency):
        assert view.figure.get_facecolor() == to_rgba(default.window)
    channel_colors = [line.get_color() for line in dock.axes[0].lines]
    window.set_theme(theme.id)
    for view in (dock, dialog, frequency):
        assert view.figure.get_facecolor() == to_rgba(theme.window)
        assert all(ax.get_facecolor() == to_rgba("#1e1e1e") for ax in view.axes)
    assert dock.axes[0].patches[0].get_facecolor() == to_rgba(theme.accent, alpha=0.7)
    assert [line.get_color() for line in dock.axes[0].lines] == channel_colors
    assert frequency.axes[1].texts[0].get_color() == theme.muted_text

    window.state.load(bgr_png[0])
    window.refresh()
    QTest.qWait(215)
    assert frequency.figure.get_facecolor() == to_rgba(theme.window)
    for ax in frequency.axes:
        assert ax.images
        assert ax.get_facecolor() == to_rgba(theme.base)
        assert ax.title.get_color() == theme.text
        assert ax.spines["left"].get_edgecolor() == to_rgba(theme.border)
