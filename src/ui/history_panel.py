"""List the current history step and any available redo steps."""

from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QListWidget


class HistoryPanel(QListWidget):
    def update_history(self, labels, current):
        """Mirror the state without emitting a navigation request."""
        if not labels and not self.count():
            return
        with QSignalBlocker(self):
            if labels != [self.item(row).text() for row in range(self.count())]:
                self.clear()
                self.addItems(labels)
                for row, label in enumerate(labels):
                    self.item(row).setToolTip(label)
            palette = self.palette()
            text = QPalette.ColorRole.Text
            normal = palette.brush(text)
            redo = palette.brush(QPalette.ColorGroup.Disabled, text)
            for row in range(self.count()):
                self.item(row).setForeground(redo if row > current else normal)
            self.setCurrentRow(current)
