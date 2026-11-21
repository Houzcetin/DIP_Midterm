import os

import cv2
import numpy as np
from PySide6.QtCore import QEvent, QSettings, QSignalBlocker, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QDialog, QDockWidget, QFileDialog, QGroupBox,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QSplitter, QSplitterHandle,
    QVBoxLayout, QWidget,
)

from core.state import ImageState
from ops.registry import get_op
from ui.histogram_view import HistogramView
from ui.history_panel import HistoryPanel
from ui.image_view import ImageView
from ui.ops_panel import OpsPanel


class _EqualizingHandle(QSplitterHandle):
    """Splitter handle that restores an even split on double-click."""

    def mouseDoubleClickEvent(self, event):
        splitter = self.splitter()
        half = sum(splitter.sizes()) // 2
        splitter.setSizes([half, half])
        event.accept()


class PanelSplitter(QSplitter):
    """Horizontal splitter for the Original/Result panels."""

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)

    def createHandle(self):
        handle = _EqualizingHandle(self.orientation(), self)
        handle.setToolTip("Drag to resize the panels; double-click to split evenly.")
        return handle


class MainWindow(QMainWindow):
    _PREVIEW_MESSAGE = "Preview — press Apply to keep"

    def __init__(self, settings=None):
        super().__init__()
        self.setWindowTitle("DIP Midterm – Image Processing Application")
        self.resize(1400, 800)

        self._settings = settings if settings is not None else QSettings("DIPMidterm", "App")
        self._preview_image = None
        self._histogram_dialog = None
        self.state = ImageState()
        self.original_view = ImageView()
        self.result_view = ImageView()
        self.original_view.viewChanged.connect(self.result_view.set_view)
        self.result_view.viewChanged.connect(self.original_view.set_view)
        self.original_view.pixelHovered.connect(self._show_pixel)
        self.result_view.pixelHovered.connect(self._show_pixel)

        # Draggable divider between the panels; double-click it to split 50/50 again.
        self._result_box = self._panel("Result", self.result_view)
        self.panel_splitter = PanelSplitter()
        self.panel_splitter.addWidget(self._panel("Original", self.original_view))
        self.panel_splitter.addWidget(self._result_box)
        self.panel_splitter.setChildrenCollapsible(False)
        self.panel_splitter.setHandleWidth(8)
        self.panel_splitter.setStretchFactor(0, 1)
        self.panel_splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.panel_splitter)

        self.ops_panel = OpsPanel()
        self.operations_dock = self._add_dock("Operations", self.ops_panel, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.ops_panel.applyRequested.connect(self.apply_operation)
        self.ops_panel.previewRequested.connect(self.preview_operation)
        self.ops_panel.previewCancelled.connect(self._clear_preview)
        self.ops_panel.resetRequested.connect(self.reset_image)

        self.histogram_view = HistogramView()
        self.history_panel = HistoryPanel()
        right = Qt.DockWidgetArea.RightDockWidgetArea
        self.histogram_dock = self._add_dock("Histogram", self.histogram_view, right)
        self.history_dock = self._add_dock("History", self.history_panel, right)
        self.resizeDocks([self.histogram_dock, self.history_dock], [470, 230], Qt.Orientation.Vertical)
        self.history_panel.currentRowChanged.connect(self._goto_history_step)
        self.history_panel.itemClicked.connect(self._clear_preview)

        self.info_label = QLabel()
        self.statusBar().addPermanentWidget(self.info_label)
        self.statusBar().messageChanged.connect(self._restore_preview_message)

        self._create_menu()
        # Route file URLs over child controls (for example spin box editors) to this window.
        for widget in self.findChildren(QWidget):
            if widget.acceptDrops():
                widget.setAcceptDrops(False)
            if isinstance(widget, (QAbstractSpinBox, QLineEdit)):
                widget.installEventFilter(self)
        self.setAcceptDrops(True)
        self.refresh()

    def _add_dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(f"{title.lower()}Dock")
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

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
        self.recent_menu = file_menu.addMenu("Recent Files")
        self._update_recent_menu()
        file_menu.addAction("Open Sample Image", self.open_sample_image)
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

        view_menu = self.menuBar().addMenu("&View")
        self._zoom_actions = []
        for label, shortcut, slot in (
            ("Fit to Window", "Ctrl+0", self.result_view.fit_to_window),
            ("Actual Size 100%", "Ctrl+1", self.result_view.actual_size),
            ("Zoom In", "Ctrl+=", self.result_view.zoom_in),
            ("Zoom Out", "Ctrl+-", self.result_view.zoom_out),
        ):
            action = view_menu.addAction(label, slot)
            action.setShortcut(shortcut)
            self._zoom_actions.append(action)
        self.compare_action = view_menu.addAction("Show Original in Result panel")
        self.compare_action.setCheckable(True)
        self.compare_action.setShortcut("Space")
        self.compare_action.setAutoRepeat(False)
        self.compare_action.toggled.connect(self._display_result)
        view_menu.addSeparator()
        for dock in (self.operations_dock, self.histogram_dock, self.history_dock):
            view_menu.addAction(dock.toggleViewAction())
        view_menu.addAction("Show Histogram Window…", self.show_histogram_window)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Keyboard Shortcuts", self.show_shortcuts)
        help_menu.addAction("About", self.show_about)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)")
        if path:
            self._open_path(path)

    def _open_path(self, path):
        try:
            self.state.load(path)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        path = os.path.abspath(path)
        recent = [entry for entry in self._recent_files()
                  if os.path.normcase(entry) != os.path.normcase(path)]
        self._settings.setValue("recentFiles", [path, *recent[:4]])
        self._update_recent_menu()
        self._finish_load()

    def _recent_files(self):
        return self._settings.value("recentFiles", [], type=list)

    def _update_recent_menu(self):
        paths = self._recent_files()[:5]
        self.recent_menu.clear()
        self.recent_menu.setEnabled(bool(paths))
        self.recent_menu.setToolTipsVisible(True)
        for path in paths:
            label = os.path.basename(path).replace("&", "&&")
            action = self.recent_menu.addAction(label)
            action.setToolTip(path)
            action.triggered.connect(lambda checked=False, path=path: self._open_path(path))

    def open_sample_image(self):
        height, width = 480, 640
        horizontal = np.linspace(0, 255, width, dtype=np.uint8)
        vertical = np.linspace(20, 230, height, dtype=np.uint8)[:, None]
        img = np.empty((height, width, 3), dtype=np.uint8)
        img[..., 0] = horizontal
        img[..., 1] = vertical
        img[..., 2] = horizontal[::-1]

        cv2.rectangle(img, (32, 28), (608, 160), (30, 30, 30), -1)
        cv2.putText(img, "COMP 4360", (53, 90), cv2.FONT_HERSHEY_SIMPLEX,
                    1.5, (245, 245, 245), 3, cv2.LINE_AA)
        cv2.putText(img, "Image Processing Sample", (55, 132), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (200, 216, 235), 2, cv2.LINE_AA)
        cv2.circle(img, (133, 299), 84, (240, 219, 82), -1, cv2.LINE_AA)
        cv2.circle(img, (133, 299), 45, (45, 45, 45), 3, cv2.LINE_AA)
        cv2.rectangle(img, (238, 225), (396, 382), (110, 78, 210), -1, cv2.LINE_AA)
        cv2.fillConvexPoly(img, np.array([(426, 383), (517, 215), (608, 383)], dtype=np.int32),
                           (238, 238, 238), cv2.LINE_AA)
        self.state.load_array(img, "sample.png")
        self._finish_load()

    def _finish_load(self):
        with QSignalBlocker(self.compare_action):
            self.compare_action.setChecked(False)
        self.result_view.fit_to_window()
        self.refresh()

    def eventFilter(self, watched, event):
        # Numeric editors claim Space by default. Let the View shortcut handle it.
        if (event.type() == QEvent.Type.ShortcutOverride
                and event.key() == Qt.Key.Key_Space
                and event.modifiers() == Qt.KeyboardModifier.NoModifier
                and self.compare_action.isEnabled()):
            event.ignore()
            return True
        return super().eventFilter(watched, event)

    @staticmethod
    def _dropped_path(event):
        return next((url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()), "")

    def dragEnterEvent(self, event):
        if self._dropped_path(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        path = self._dropped_path(event)
        if path:
            self._open_path(path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def show_histogram_window(self):
        if self._histogram_dialog is None:
            dialog = QDialog(self)
            dialog.setWindowTitle("Histogram")
            dialog.resize(700, 560)
            self._dialog_histogram = HistogramView(dialog)
            QVBoxLayout(dialog).addWidget(self._dialog_histogram)
            self._histogram_dialog = dialog
        self._dialog_histogram.update_images(self.state.original, self._displayed_result())
        self._histogram_dialog.show()
        self._histogram_dialog.raise_()
        self._histogram_dialog.activateWindow()

    def show_shortcuts(self):
        shortcuts = []
        for menu_action in self.menuBar().actions():
            for action in menu_action.menu().actions():
                if action.shortcuts():
                    keys = ", ".join(key.toString(QKeySequence.SequenceFormat.NativeText)
                                     for key in action.shortcuts())
                    label = action.text().replace("&", "").rstrip(".…")
                    shortcuts.append(f"{keys}  —  {label}")
        shortcuts.extend((
            "",
            "Mouse wheel  —  Zoom around the pointer",
            "Left drag  —  Pan a zoomed image",
            "Double-click  —  Fit to Window",
        ))
        QMessageBox.information(self, "Keyboard Shortcuts", "\n".join(shortcuts))

    def show_about(self):
        QMessageBox.about(self, "About DIP Midterm",
                          "COMP 4360 Midterm\nDigital Image Processing\n\nBuilt with PySide6 and OpenCV.")

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
            self._preview_image = op.func(self.state.current, **params)
            self._display_result()
        except Exception as error:
            # No modal dialog here: previews fire while sliders are dragged.
            self._clear_preview()
            self.statusBar().showMessage(f"Preview failed: {error}", 5000)
            return
        self.statusBar().showMessage(self._PREVIEW_MESSAGE)

    def undo(self):
        self.state.undo()
        self.refresh()

    def redo(self):
        self.state.redo()
        self.refresh()

    def _goto_history_step(self, row):
        if row >= 0:
            self.state.goto(row)
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
        labels = self.state.history_labels()
        self.history_panel.update_history(labels, self.state.index)
        self.undo_action.setEnabled(self.state.can_undo())
        self.redo_action.setEnabled(self.state.can_redo())
        self.reset_action.setEnabled(self.state.has_image())
        self.promote_action.setEnabled(self.state.can_undo() or self.state.can_redo())
        for action in (*self._zoom_actions, self.compare_action):
            action.setEnabled(self.state.has_image())
        self._update_image_info(len(labels) - 1)

    def _clear_preview(self):
        self.ops_panel.cancel_pending_preview()
        self._preview_image = None
        self._display_result()
        self.statusBar().clearMessage()

    def _displayed_result(self):
        if self.compare_action.isChecked():
            return self.state.original
        if self._preview_image is not None:
            return self._preview_image
        return self.state.current

    def _display_result(self):
        img = self._displayed_result()
        title = "Result — showing Original" if self.compare_action.isChecked() else "Result"
        self._result_box.setTitle(title)
        self.result_view.set_image(img)
        self.histogram_view.update_images(self.state.original, img)
        if self._histogram_dialog is not None and self._histogram_dialog.isVisible():
            self._dialog_histogram.update_images(self.state.original, img)

    def _show_pixel(self, x, y, value):
        if isinstance(value, tuple):
            b, g, r = value
            channels = f"R,G,B={r},{g},{b}"
        else:
            channels = f"Gray={value}"
        self.statusBar().showMessage(f"x={x}, y={y} | {channels}", 1500)

    def _restore_preview_message(self, message):
        if not message and self._preview_image is not None:
            self.statusBar().showMessage(self._PREVIEW_MESSAGE)

    def _update_image_info(self, last_step):
        img = self.state.current
        if img is None:
            self.info_label.setText("Open an image to start (Ctrl+O)")
            self.info_label.setToolTip("")
            return
        h, w = img.shape[:2]
        ch = 1 if img.ndim == 2 else img.shape[2]
        name = os.path.basename(self.state.path or "")
        self.info_label.setText(
            f"{name}  |  {w}×{h}  |  {ch} channel(s)  |  step {self.state.index}/{last_step}"
        )
        self.info_label.setToolTip(str(self.state.path or ""))
