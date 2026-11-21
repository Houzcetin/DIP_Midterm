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


def main():
    app = QApplication(sys.argv)
    configure_appearance(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
