from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QGroupBox, QFileDialog, QMessageBox)

from core.state import ImageState
from ui.image_view import ImageView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIP Midterm – Image Processing Application")
        self.resize(1200, 700)

        self.state = ImageState()
        self.original_view = ImageView()
        self.result_view = ImageView()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._panel("Original", self.original_view))
        layout.addWidget(self._panel("Result", self.result_view))
        self.setCentralWidget(central)

        self._create_menu()
        self.statusBar().showMessage("Open an image to start (Ctrl+O)")

    def _panel(self, title, view):
        box = QGroupBox(title)
        QVBoxLayout(box).addWidget(view)
        return box

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("&File")

        open_act = QAction("&Open...", self)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        open_act.triggered.connect(self.open_image)

        save_act = QAction("&Save Result As...", self)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        save_act.triggered.connect(self.save_image)

        reset_act = QAction("&Reset to Original", self)
        reset_act.setShortcut("Ctrl+R")
        reset_act.triggered.connect(self.reset_image)

        exit_act = QAction("E&xit", self)
        exit_act.triggered.connect(self.close)

        file_menu.addAction(open_act)
        file_menu.addAction(save_act)
        file_menu.addSeparator()
        file_menu.addAction(reset_act)
        file_menu.addSeparator()
        file_menu.addAction(exit_act)

    # ---------- actions ----------
    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if not path:
            return
        try:
            self.state.load(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        self.refresh()

    def save_image(self):
        if not self._require_image():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Result", "result.png",
            "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)")
        if not path:
            return
        try:
            self.state.save(path)
            self.statusBar().showMessage(f"Saved: {path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def reset_image(self):
        if not self._require_image():
            return
        self.state.reset()
        self.refresh()

    # ---------- helpers ----------
    def _require_image(self):
        if not self.state.has_image():
            QMessageBox.information(self, "No image", "Please open an image first.")
            return False
        return True

    def refresh(self):
        self.original_view.set_image(self.state.original)
        self.result_view.set_image(self.state.current)
        img = self.state.current
        h, w = img.shape[:2]
        ch = 1 if img.ndim == 2 else img.shape[2]
        self.statusBar().showMessage(f"{self.state.path}  |  {w}×{h}  |  {ch} channel(s)")
