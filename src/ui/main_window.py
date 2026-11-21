import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication, QDockWidget, QFileDialog, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QVBoxLayout, QWidget,
)

from core.state import ImageState
from ops.registry import get_op
from ui.image_view import ImageView
from ui.ops_panel import OpsPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DIP Midterm – Image Processing Application")
        self.resize(1400, 800)

        self.state = ImageState()
        self.original_view = ImageView()
        self.result_view = ImageView()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.addWidget(self._panel("Original", self.original_view))
        layout.addWidget(self._panel("Result", self.result_view))
        self.setCentralWidget(central)

        self.ops_panel = OpsPanel()
        dock = QDockWidget("Operations", self)
        dock.setWidget(self.ops_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.ops_panel.applyRequested.connect(self.apply_operation)
        self.ops_panel.previewRequested.connect(self.preview_operation)
        self.ops_panel.previewCancelled.connect(self._clear_preview)
        self.ops_panel.resetRequested.connect(self.reset_image)

        # Image info lives in a permanent widget so temporary messages
        # (preview, saved, errors) never hide it.
        self.info_label = QLabel()
        self.statusBar().addPermanentWidget(self.info_label)

        self._create_menu()
        self.refresh()

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

        exit_act = QAction("E&xit", self)
        exit_act.triggered.connect(self.close)

        file_menu.addAction(open_act)
        file_menu.addAction(save_act)
        file_menu.addSeparator()
        file_menu.addAction(exit_act)

        edit_menu = self.menuBar().addMenu("&Edit")
        self.undo_action = edit_menu.addAction("&Undo", self.undo)
        self.undo_action.setShortcut("Ctrl+Z")
        self.redo_action = edit_menu.addAction("&Redo", self.redo)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        edit_menu.addSeparator()
        self.reset_action = edit_menu.addAction("Reset to &Original", self.reset_image)
        self.reset_action.setShortcut("Ctrl+R")
        self.promote_action = edit_menu.addAction("&Use Result as Original", self.set_result_as_original)

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

    def apply_operation(self, op_id, params):
        self.ops_panel.cancel_pending_preview()
        if not self._require_image():
            return

        try:
            op = get_op(op_id)
            if not op.live:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                result = op.func(self.state.current, **params)
                summary = ", ".join(f"{key}={value}" for key, value in params.items())
                label = f"{op.label} ({summary})" if summary else op.label
                self.state.apply(label, result)
            finally:
                if not op.live:
                    QApplication.restoreOverrideCursor()
        except Exception as error:
            self._clear_preview()
            QMessageBox.warning(self, "Operation failed", str(error))
            return
        self.refresh()

    def preview_operation(self, op_id, params):
        if not self.state.has_image():
            return
        try:
            op = get_op(op_id)
            result = op.func(self.state.current, **params)
            self.result_view.set_image(result)
        except Exception as error:
            # No modal dialog here: previews fire while sliders are dragged.
            self._clear_preview()
            self.statusBar().showMessage(f"Preview failed: {error}", 5000)
            return
        self.statusBar().showMessage("Preview — press Apply to keep")

    def undo(self):
        self.state.undo()
        self.refresh()

    def redo(self):
        self.state.redo()
        self.refresh()

    def reset_image(self):
        if not self._require_image():
            return
        self.state.reset()
        self.refresh()

    def set_result_as_original(self):
        self.state.set_result_as_original()
        self.refresh()

    def _require_image(self):
        if not self.state.has_image():
            QMessageBox.information(self, "No image", "Please open an image first.")
            return False
        return True

    def refresh(self):
        self.original_view.set_image(self.state.original)
        self._clear_preview()
        self.undo_action.setEnabled(self.state.can_undo())
        self.redo_action.setEnabled(self.state.can_redo())
        self.reset_action.setEnabled(self.state.has_image())
        self.promote_action.setEnabled(self.state.can_undo() or self.state.can_redo())

    def _clear_preview(self):
        self.ops_panel.cancel_pending_preview()
        img = self.state.current
        self.result_view.set_image(img)
        self.statusBar().clearMessage()
        if img is None:
            self.info_label.setText("Open an image to start (Ctrl+O)")
            return
        h, w = img.shape[:2]
        ch = 1 if img.ndim == 2 else img.shape[2]
        last_step = len(self.state.history_labels()) - 1
        name = os.path.basename(self.state.path or "")
        self.info_label.setText(
            f"{name}  |  {w}×{h}  |  {ch} channel(s)  |  step {self.state.index}/{last_step}"
        )
        self.info_label.setToolTip(str(self.state.path or ""))
