"""Provide the Manifest-inspired palettes, control styles, and icons."""

from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from ui import avatars


@dataclass(frozen=True)
class Theme:
    """Colors for the application chrome and plot decorations."""

    id: str
    member: str
    color_name: str
    accent: str
    on_accent: str
    window: str
    base: str
    alternate_base: str
    button: str
    dock_title: str
    border: str
    text: str
    muted_text: str
    disabled_text: str
    accent_hover: str
    accent_soft: str

    @property
    def label(self) -> str:
        return f"{self.member} — {self.color_name}"


def mix(c1: str, c2: str, t: float) -> str:
    """Interpolate two RGB hex colors with a fraction t of the second color."""
    first = bytes.fromhex(c1.removeprefix("#"))
    second = bytes.fromhex(c2.removeprefix("#"))
    channels = bytes(round(a + (b - a) * t) for a, b in zip(first, second))
    return "#" + channels.hex()


def _make_theme(theme_id: str, member: str, color_name: str, accent: str, on_accent: str) -> Theme:
    button = mix("#30363e", accent, 0.05)
    return Theme(
        id=theme_id,
        member=member,
        color_name=color_name,
        accent=accent,
        on_accent=on_accent,
        window=mix("#25282d", accent, 0.05),
        base="#1e1e1e",
        alternate_base="#2a2e35",
        button=button,
        dock_title=mix("#2e343c", accent, 0.05),
        border="#3a414a",
        text="#e1e6ed",
        muted_text="#c3cad4",
        disabled_text="#87919e",
        accent_hover=mix(accent, "#ffffff", 0.18),
        accent_soft=mix(button, accent, 0.22),
    )


THEMES: dict[str, Theme] = {
    spec[0]: _make_theme(*spec)
    for spec in (
        ("mina", "Mina", "Kırmızı", "#E5484D", "#141414"),
        ("esin", "Esin", "Sarı", "#F5C518", "#1B1B1B"),
        ("zeynep", "Zeynep Sude", "Mavi", "#3B82F6", "#1B1B1B"),
        ("lidya", "Lidya", "Pembe", "#EC6BB4", "#1B1B1B"),
        ("sueda", "Sueda", "Yeşil", "#2FB86A", "#1B1B1B"),
        ("hilal", "Hilal", "Mor", "#9B6BF2", "#1B1B1B"),
    )
}
DEFAULT_THEME = "zeynep"


def get_theme(theme_id: str | None) -> Theme:
    """Resolve a stored theme ID, falling back to the default when invalid."""
    default = THEMES[DEFAULT_THEME]
    return THEMES.get(theme_id, default) if isinstance(theme_id, str) else default


def build_palette(theme: Theme) -> QPalette:
    """Build the Qt palette shared by the windows and native controls."""
    roles = QPalette.ColorRole
    palette = QPalette()
    for role, color in {
        roles.Window: theme.window,
        roles.WindowText: theme.text,
        roles.Base: theme.base,
        roles.AlternateBase: theme.alternate_base,
        roles.Text: theme.text,
        roles.Button: theme.button,
        roles.ButtonText: theme.text,
        roles.ToolTipBase: "#333b47",
        roles.ToolTipText: "#f0f4f9",
        roles.Light: "#4b5562",
        roles.Mid: "#353c46",
        roles.Dark: "#1c2025",
        roles.Shadow: "#151719",
        roles.Highlight: theme.accent,
        roles.HighlightedText: theme.on_accent,
        roles.Link: theme.accent,
        roles.PlaceholderText: "#a0aab7",
    }.items():
        palette.setColor(role, QColor(color))
    for role in (roles.WindowText, roles.Text, roles.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(theme.disabled_text))
    return palette


def build_stylesheet(theme: Theme) -> str:
    """Style accented control states while keeping the main surfaces dark."""
    return f"""
        QDockWidget::title {{
            background: {theme.dock_title};
            border-left: 3px solid {theme.accent};
            padding-left: 5px;
        }}
        QSplitter::handle:horizontal {{
            background: {theme.alternate_base};
            margin: 40px 2px;
            border-radius: 2px;
        }}
        QSplitter::handle:horizontal:hover {{
            background: {theme.accent};
        }}
        QGroupBox {{
            border: 1px solid {theme.border};
            border-radius: 5px;
            margin-top: 0.65em;
            padding-top: 0.35em;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 8px;
            padding: 0 4px;
            color: {theme.accent};
        }}
        QToolBox::tab {{
            background: {theme.button};
            border: 1px solid {theme.border};
            border-bottom-width: 2px;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QToolBox::tab:selected {{
            border-bottom-color: {theme.accent};
            color: {theme.accent};
        }}
        QPushButton {{
            background: {theme.button};
            border: 1px solid {theme.border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QPushButton:hover, QPushButton:focus {{
            border-color: {theme.accent};
        }}
        QPushButton:pressed {{
            background: {theme.accent_soft};
        }}
        QSlider::groove:horizontal {{
            background: {theme.border};
            border-radius: 2px;
            height: 4px;
        }}
        QSlider::sub-page:horizontal {{
            background: {theme.accent};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {theme.accent};
            border-radius: 6px;
            margin: -4px 0;
            width: 12px;
        }}
        QSlider::handle:horizontal:hover {{
            background: {theme.accent_hover};
        }}
        QComboBox:focus {{
            border: 1px solid {theme.accent};
            border-radius: 3px;
        }}
        /* Keep Fusion's native step buttons visible when the editor has focus. */
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {theme.accent};
        }}
        QMenu::item:selected, QListWidget::item:selected {{
            background: {theme.accent};
            color: {theme.on_accent};
        }}
    """


def apply_theme(app: QApplication, theme: Theme) -> None:
    """Update the application's palette, stylesheet, and icon together."""
    app.setPalette(build_palette(theme))
    app.setStyleSheet(build_stylesheet(theme))
    app.setWindowIcon(app_icon(theme))


def app_icon(theme: Theme) -> QIcon:
    """Use the member's pixel-art head, or a rounded DIP badge if it is missing."""
    try:
        return avatars.head_icon(theme.id)
    except FileNotFoundError:
        return _badge_icon(theme)


def theme_icon(theme: Theme) -> QIcon:
    """Menu icon for a theme: the member's head, or the accent swatch as fallback."""
    try:
        return avatars.head_icon(theme.id)
    except FileNotFoundError:
        return swatch_icon(theme)


def _badge_icon(theme: Theme) -> QIcon:
    """Paint the rounded DIP icon in the selected accent."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    with QPainter(pixmap) as painter:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(theme.accent))
        painter.drawRoundedRect(QRectF(2, 2, 60, 60), 12, 12)
        painter.setPen(QColor(theme.on_accent))
        painter.setFont(QFont("Sans Serif", 16, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "DIP")
    return QIcon(pixmap)


def swatch_icon(theme: Theme, size: int = 16) -> QIcon:
    """Paint a menu-sized accent swatch with a subtle outline."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    with QPainter(pixmap) as painter:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(theme.accent))
        painter.setPen(QPen(QColor(mix(theme.accent, theme.base, 0.3))))
        painter.drawEllipse(QRectF(1, 1, size - 2, size - 2))
    return QIcon(pixmap)
