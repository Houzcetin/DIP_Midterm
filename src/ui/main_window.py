import logging
import os

from PySide6.QtCore import QEvent, QSettings, QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QDialog, QDockWidget, QFileDialog, QGroupBox,
    QLabel, QLineEdit, QMainWindow, QMessageBox, QSplitter, QSplitterHandle,
    QVBoxLayout, QWidget,
)

from core.samples import SAMPLES
from core.state import ImageState
from ops import auto
from ops.registry import OPERATIONS, get_op
from ui.auto_report import AutoReportDialog
from ui.histogram_view import HistogramView
from ui.frequency_view import FrequencyView
from ui.history_panel import HistoryPanel
from ui.i18n import LANGUAGES, current_language, language_changed, set_language as set_ui_language, tr
from ui.image_view import ImageView
from ui.ops_panel import OpsPanel, choice_label
from ui import avatars
from ui.themes import THEMES, apply_theme, get_theme, theme_icon


_LOG = logging.getLogger(__name__)
_OPERATIONS_BY_LABEL = {op.label: op for op in OPERATIONS}
# Qt dialogs follow the app language, while native dialogs follow the OS language.
_FILE_DIALOG_OPTIONS = QFileDialog.Option.DontUseNativeDialog


class _EqualizingHandle(QSplitterHandle):
    """Splitter handle that restores an even split on double-click."""

    def mouseDoubleClickEvent(self, event):
        splitter = self.splitter()
        half = sum(splitter.sizes()) // 2
        splitter.setSizes([half, half])
        event.accept()


class PanelSplitter(QSplitter):
    """Horizontal splitter for the Original/Result panels."""

    _HINT = "Drag to resize the panels; double-click to split evenly."

    def __init__(self):
        super().__init__(Qt.Orientation.Horizontal)

    def createHandle(self):
        handle = _EqualizingHandle(self.orientation(), self)
        handle.setToolTip(tr(self._HINT))
        return handle

    def retranslate(self):
        for handle in self.findChildren(_EqualizingHandle):
            handle.setToolTip(tr(self._HINT))


class MainWindow(QMainWindow):
    themeChanged = Signal(object)

    _PREVIEW_MESSAGE = "Preview — press Apply to keep"
    _STRETCH_HINT = "sizes differ — original stretched"

    def __init__(self, settings=None):
        super().__init__()
        self.resize(1400, 800)

        self._settings = settings if settings is not None else QSettings("DIPMidterm", "App")
        set_ui_language(self._settings.value("language"))
        self._theme = get_theme(self._settings.value("theme"))
        self._preview_image = None
        self._histogram_dialog = None
        self._frequency_dialog = None
        self.auto_report_dialog = None
        self._stretch_hint_shown = False
        self.state = ImageState()
        self.original_view = ImageView()
        self.result_view = ImageView()
        self.original_view.viewChanged.connect(self.result_view.set_view)
        self.result_view.viewChanged.connect(self.original_view.set_view)
        self.original_view.pixelHovered.connect(self._show_pixel)
        self.result_view.pixelHovered.connect(self._show_pixel)

        # Draggable divider between the panels; double-click it to split 50/50 again.
        self._result_box = self._panel("Result", self.result_view)
        self._original_box = self._panel("Original", self.original_view)
        self.panel_splitter = PanelSplitter()
        self.panel_splitter.addWidget(self._original_box)
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
        self.ops_panel.paramsChanged.connect(self._update_frequency_view)
        self.ops_panel.resetRequested.connect(self.reset_image)
        self.ops_panel.autoEnhanceRequested.connect(self.auto_enhance)
        self.themeChanged.connect(self._show_member)
        self._show_member(self._theme)

        self.histogram_view = HistogramView(theme=self._theme)
        self.themeChanged.connect(self.histogram_view.apply_theme)
        self.history_panel = HistoryPanel()
        right = Qt.DockWidgetArea.RightDockWidgetArea
        self.histogram_dock = self._add_dock("Histogram", self.histogram_view, right)
        self.history_dock = self._add_dock("History", self.history_panel, right)
        self.resizeDocks([self.histogram_dock, self.history_dock], [470, 230], Qt.Orientation.Vertical)
        self.history_panel.currentRowChanged.connect(self._goto_history_step)
        self.history_panel.itemClicked.connect(self._clear_preview)

        self.info_label = QLabel()
        self._status_source = ""
        self._status_fields = {}
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self.statusBar().clearMessage)
        self.statusBar().addPermanentWidget(self.info_label)
        self.statusBar().messageChanged.connect(self._restore_preview_message)

        self._menu_texts = []
        self._create_menu()
        language_changed.changed.connect(self._retranslate)
        self._retranslate()
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
        def add_menu(parent, source):
            menu = parent.addMenu("")
            self._menu_texts.append((menu.setTitle, source))
            return menu

        def add_action(menu, source, slot=None):
            action = QAction(menu)
            if slot is not None:
                action.triggered.connect(slot)
            menu.addAction(action)
            self._menu_texts.append((action.setText, source))
            return action

        file_menu = add_menu(self.menuBar(), "&File")
        open_act = add_action(file_menu, "&Open...", self.open_image)
        open_act.setShortcut(QKeySequence.StandardKey.Open)
        self.recent_menu = add_menu(file_menu, "Recent Files")
        self._update_recent_menu()
        samples_menu = add_menu(file_menu, "Sample Images")
        samples_menu.setToolTipsVisible(True)
        for name, (label, suggestion, _) in SAMPLES.items():
            action = QAction(samples_menu)
            samples_menu.addAction(action)
            self._menu_texts.extend((
                (lambda text, action=action: action.setText(text.replace("&", "&&")), label),
                (action.setToolTip, suggestion),
            ))
            action.triggered.connect(lambda checked=False, name=name: self.open_sample_image(name))
        save_act = add_action(file_menu, "&Save Result As...", self.save_image)
        save_act.setShortcut(QKeySequence.StandardKey.Save)
        file_menu.addSeparator()
        add_action(file_menu, "E&xit", self.close)

        edit_menu = add_menu(self.menuBar(), "&Edit")
        self.undo_action = add_action(edit_menu, "&Undo", self.undo)
        self.undo_action.setShortcut("Ctrl+Z")
        self.redo_action = add_action(edit_menu, "&Redo", self.redo)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        edit_menu.addSeparator()
        self.reset_action = add_action(edit_menu, "Reset to &Original", self.reset_image)
        self.reset_action.setShortcut("Ctrl+R")
        self.promote_action = add_action(edit_menu, "&Use Result as Original", self.set_result_as_original)
        self.auto_enhance_action = add_action(edit_menu, "Auto Enhance...", self.auto_enhance)
        self.auto_enhance_action.setShortcut("Ctrl+E")

        view_menu = add_menu(self.menuBar(), "&View")
        self._zoom_actions = []
        for label, shortcut, slot in (
            ("Fit to Window", "Ctrl+0", self.result_view.fit_to_window),
            ("Actual Size 100%", "Ctrl+1", self.result_view.actual_size),
            ("Zoom In", "Ctrl+=", self.result_view.zoom_in),
            ("Zoom Out", "Ctrl+-", self.result_view.zoom_out),
        ):
            action = add_action(view_menu, label, slot)
            action.setShortcut(shortcut)
            self._zoom_actions.append(action)
        self.compare_action = add_action(view_menu, "Show Original in Result panel")
        self.compare_action.setCheckable(True)
        self.compare_action.setShortcut("Space")
        self.compare_action.setAutoRepeat(False)
        self.compare_action.toggled.connect(self._display_result)
        self.wipe_action = add_action(view_menu, "Before/After Slider")
        self.wipe_action.setCheckable(True)
        self.wipe_action.setShortcut("Ctrl+B")
        self.wipe_action.toggled.connect(self._update_wipe)
        view_menu.addSeparator()
        for dock in (self.operations_dock, self.histogram_dock, self.history_dock):
            view_menu.addAction(dock.toggleViewAction())
        add_action(view_menu, "Show Histogram Window…", self.show_histogram_window)
        inspector_action = add_action(view_menu, "Frequency Inspector…", self.show_frequency_inspector)
        inspector_action.setShortcut("Ctrl+F")
        view_menu.addSeparator()
        theme_menu = add_menu(view_menu, "Theme")
        theme_group = QActionGroup(theme_menu)
        theme_group.setExclusive(True)
        self._theme_actions = {}
        for theme in THEMES.values():
            action = theme_menu.addAction(theme_icon(theme), "")
            action.setCheckable(True)
            action.setData(theme.id)
            theme_group.addAction(action)
            self._theme_actions[theme.id] = action
        self._theme_actions[self._theme.id].setChecked(True)
        theme_group.triggered.connect(lambda action: self.set_theme(action.data()))

        language_menu = add_menu(view_menu, "Language")
        language_group = QActionGroup(language_menu)
        language_group.setExclusive(True)
        self._language_actions = {}
        for code, label in LANGUAGES.items():
            action = language_menu.addAction(label)
            action.setCheckable(True)
            action.setData(code)
            language_group.addAction(action)
            self._language_actions[code] = action
        language_group.triggered.connect(lambda action: self.set_language(action.data()))

        help_menu = add_menu(self.menuBar(), "&Help")
        add_action(help_menu, "Keyboard Shortcuts", self.show_shortcuts)
        add_action(help_menu, "About", self.show_about)

    def set_language(self, language: str | None) -> None:
        """Apply the chosen UI language and persist it for the next launch."""
        set_ui_language(language)
        self._settings.setValue("language", current_language())

    def _retranslate(self):
        self.setWindowTitle(tr("DIP Midterm – Image Processing Application"))
        for setter, source in self._menu_texts:
            setter(tr(source))
        for dock, source in ((self.operations_dock, "Operations"), (self.histogram_dock, "Histogram"),
                             (self.history_dock, "History")):
            dock.setWindowTitle(tr(source))
        for theme in THEMES.values():
            self._theme_actions[theme.id].setText(theme.label)
        self._language_actions[current_language()].setChecked(True)
        self._original_box.setTitle(tr("Original"))
        self._update_result_title()
        self.panel_splitter.retranslate()
        self.original_view.update()
        self.result_view.update()
        self.ops_panel.retranslate()
        self.histogram_view.retranslate()
        if self._histogram_dialog is not None:
            self._histogram_dialog.setWindowTitle(tr("Histogram"))
            self._dialog_histogram.retranslate()
        if self._frequency_dialog is not None:
            self._frequency_dialog.retranslate()
        if self.auto_report_dialog is not None:
            self.auto_report_dialog.retranslate()
        self._update_history()
        self._render_status()

    def set_theme(self, theme_id: str | None) -> None:
        """Apply the selected appearance and persist it for the next launch."""
        theme = get_theme(theme_id)
        apply_theme(QApplication.instance(), theme)
        self._theme = theme
        self._settings.setValue("theme", theme.id)
        self._theme_actions[theme.id].setChecked(True)
        self.themeChanged.emit(theme)

    def _show_member(self, theme):
        """Put the theme member's figure in the empty panel and the operations header."""
        self.ops_panel.set_member(theme)
        try:
            figure = avatars.figure(theme.id)
        except FileNotFoundError:
            figure = None
        self.original_view.set_placeholder_figure(figure)

    def open_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Open Image"), "",
            tr("Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff)"), "", _FILE_DIALOG_OPTIONS)
        if path:
            self._open_path(path)

    def _show_file_error(self, source, path, error):
        _LOG.debug("Image file operation failed for %s", path, exc_info=True)
        if isinstance(error, FileNotFoundError):
            source = "File not found: {path}"
        elif isinstance(error, PermissionError):
            source = "Permission denied: {path}"
        QMessageBox.critical(self, tr("Error"), tr(source).format(path=path))

    def _open_path(self, path):
        try:
            self.state.load(path)
        except Exception as error:
            self._show_file_error("Could not open image: {path}", path, error)
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

    def open_sample_image(self, name="shapes"):
        _, suggestion, generate = SAMPLES[name]
        self.state.load_array(generate(), f"sample_{name}.png")
        self._finish_load()
        self._show_status(suggestion, 6500)

    def _finish_load(self):
        self._stretch_hint_shown = False
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
            dialog.setWindowTitle(tr("Histogram"))
            dialog.resize(700, 560)
            self._dialog_histogram = HistogramView(dialog, theme=self._theme)
            self.themeChanged.connect(self._dialog_histogram.apply_theme)
            QVBoxLayout(dialog).addWidget(self._dialog_histogram)
            self._histogram_dialog = dialog
        self._dialog_histogram.update_images(self.state.original, self._displayed_result())
        self._histogram_dialog.show()
        self._histogram_dialog.raise_()
        self._histogram_dialog.activateWindow()

    def show_frequency_inspector(self):
        if self._frequency_dialog is None:
            self._frequency_dialog = FrequencyView(self, theme=self._theme)
            self.themeChanged.connect(self._frequency_dialog.apply_theme)
        self._frequency_dialog.show()
        self._update_frequency_view()
        self._frequency_dialog.raise_()
        self._frequency_dialog.activateWindow()

    def _update_frequency_view(self, op_id="frequency_filter"):
        dialog = self._frequency_dialog
        if op_id == "frequency_filter" and dialog is not None and dialog.isVisible():
            dialog.update_image(self.state.current, self.ops_panel.current_params(op_id))

    def show_shortcuts(self):
        shortcuts = []
        for menu_action in self.menuBar().actions():
            for action in menu_action.menu().actions():
                if action.shortcuts():
                    keys = ", ".join(key.toString(QKeySequence.SequenceFormat.NativeText)
                                     for key in action.shortcuts())
                    label = action.text().replace("&", "").rstrip(".…")
                    shortcuts.append(f"{keys}  —  {label}")
        shortcuts.extend(map(tr, (
            "",
            "Mouse wheel  —  Zoom around the pointer",
            "Left drag  —  Pan a zoomed image",
            "Drag the Before/After divider  —  Move the wipe",
            "Double-click  —  Fit to Window",
        )))
        QMessageBox.information(self, tr("Keyboard Shortcuts"), "\n".join(shortcuts))

    def show_about(self):
        QMessageBox.about(
            self, tr("About DIP Midterm"),
            tr("COMP 4360 Midterm\nDigital Image Processing\n\nBuilt with PySide6 and OpenCV."))

    def save_image(self):
        if not self._require_image():
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save Result"), "result.png",
            tr("PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp)"), "", _FILE_DIALOG_OPTIONS)
        if not path:
            return
        try:
            self.state.save(path)
            self._show_status("Saved: {path}", 5000, path=path)
        except Exception as error:
            self._show_file_error("Could not save image: {path}", path, error)

    def auto_enhance(self) -> None:
        if not self.state.has_image():
            return
        # Compare and preview are temporary views of the current history step.
        with QSignalBlocker(self.compare_action):
            self.compare_action.setChecked(False)
        self._clear_preview()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = auto.run(self.state.current)
        except Exception:
            _LOG.debug("Auto Enhance failed", exc_info=True)
            self._show_status("Auto Enhance could not process this image.", 5000)
            return
        finally:
            QApplication.restoreOverrideCursor()

        for entry in result.steps:
            if not self.apply_operation(entry.step.op_id, entry.step.params, result=entry.output):
                return
        if self.auto_report_dialog is None:
            self.auto_report_dialog = AutoReportDialog(self, self._localized_history_label)
        self.auto_report_dialog.set_result(result)
        self.auto_report_dialog.show()
        self.auto_report_dialog.raise_()
        self.auto_report_dialog.activateWindow()

    def apply_operation(self, op_id, params, *, result=None) -> bool:
        self.ops_panel.cancel_pending_preview()
        if not self._require_image():
            return False

        op = None
        try:
            op = get_op(op_id)
            if not op.live:
                QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                if result is None:
                    result = op.func(self.state.current, **params)
                self.state.apply(op.label, result, params=params)
            finally:
                if not op.live:
                    QApplication.restoreOverrideCursor()
        except Exception:
            _LOG.debug("Operation %s failed", op_id, exc_info=True)
            self._clear_preview()
            operation = tr(op.label) if op is not None else op_id
            QMessageBox.warning(self, tr("Operation failed"), tr("Could not apply {operation}.").format(
                operation=operation))
            return False
        self.refresh()
        return True

    def preview_operation(self, op_id, params):
        if not self.state.has_image():
            return
        op = None
        try:
            op = get_op(op_id)
            self._preview_image = op.func(self.state.current, **params)
            if self._status_source != self._STRETCH_HINT:
                self._show_status(self._PREVIEW_MESSAGE)
            self._display_result()
        except Exception:
            # No modal dialog here: previews fire while sliders are dragged.
            _LOG.debug("Preview of %s failed", op_id, exc_info=True)
            self._clear_preview()
            self._show_status("Preview failed: {operation}", 5000,
                              operation=lambda: tr(op.label) if op else op_id)
            return

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
            QMessageBox.information(self, tr("No image"), tr("Please open an image first."))
            return False
        return True

    def refresh(self):
        self.original_view.set_image(self.state.original)
        self._clear_preview()
        self._update_history()
        self.undo_action.setEnabled(self.state.can_undo())
        self.redo_action.setEnabled(self.state.can_redo())
        self.reset_action.setEnabled(self.state.has_image())
        self.auto_enhance_action.setEnabled(self.state.has_image())
        self.ops_panel.auto_enhance_button.setEnabled(self.state.has_image())
        self.promote_action.setEnabled(self.state.can_undo() or self.state.can_redo())
        for action in (*self._zoom_actions, self.compare_action, self.wipe_action):
            action.setEnabled(self.state.has_image())
        self._update_frequency_view()

    def _update_history(self):
        formatter = self._localized_history_label if current_language() == "tr" else None
        labels = self.state.history_labels(formatter)
        self.history_panel.update_history(labels, self.state.index)
        self._update_image_info(len(labels) - 1)

    @staticmethod
    def _localized_history_label(label, params):
        op = _OPERATIONS_BY_LABEL.get(label)
        if op is None:
            return tr(label) if label in ("Original", "Reset") else label
        specs = {param.name: param for param in op.params}
        parts = []
        for name, value in params.items():
            spec = specs.get(name)
            if spec is not None:
                name = tr(spec.label)
                if spec.kind == "choice":
                    value = tr(choice_label(value))
                elif spec.kind == "bool":
                    value = tr("Yes" if value else "No")
            parts.append(f"{name}={value}")
        title = tr(label)
        return f"{title} ({', '.join(parts)})" if parts else title

    def _clear_preview(self):
        self.ops_panel.cancel_pending_preview()
        self._preview_image = None
        self._show_status("")
        self._display_result()

    def _displayed_result(self):
        if self.compare_action.isChecked():
            return self.state.original
        if self._preview_image is not None:
            return self._preview_image
        return self.state.current

    def _display_result(self):
        img = self._displayed_result()
        self._update_result_title()
        self.result_view.set_image(img)
        self._update_wipe()
        self.histogram_view.update_images(self.state.original, img)
        if self._histogram_dialog is not None and self._histogram_dialog.isVisible():
            self._dialog_histogram.update_images(self.state.original, img)

    def _update_result_title(self):
        title = "Result — showing Original" if self.compare_action.isChecked() else "Result"
        self._result_box.setTitle(tr(title))

    def _update_wipe(self):
        enabled = self.wipe_action.isChecked() and not self.compare_action.isChecked()
        original = self.state.original if enabled else None
        self.result_view.set_compare_image(original)
        if (original is not None and not self._stretch_hint_shown
                and original.shape[:2] != self._displayed_result().shape[:2]):
            self._stretch_hint_shown = True
            self._show_status(self._STRETCH_HINT, 4000)

    def _show_pixel(self, x, y, value):
        if self._status_source == self._STRETCH_HINT:
            return
        coordinates = f"x={x}, y={y}"
        if isinstance(value, tuple):
            b, g, r = value
            self._show_status("{coordinates} | R,G,B={r},{g},{b}", 1500,
                              coordinates=coordinates, r=r, g=g, b=b)
        else:
            self._show_status("{coordinates} | Gray={value}", 1500, coordinates=coordinates, value=value)

    def _show_status(self, source, timeout=0, **fields):
        self._status_timer.stop()
        self._status_source = source
        self._status_fields = fields
        self._render_status()
        if timeout:
            self._status_timer.start(timeout)

    def _render_status(self):
        fields = {key: value() if callable(value) else value for key, value in self._status_fields.items()}
        self.statusBar().showMessage(tr(self._status_source).format(**fields))

    def _restore_preview_message(self, message):
        if not message:
            self._status_timer.stop()
            self._status_source = ""
            self._status_fields = {}
            if self._preview_image is not None:
                self._show_status(self._PREVIEW_MESSAGE)

    def _update_image_info(self, last_step):
        img = self.state.current
        if img is None:
            self.info_label.setText(tr("Open an image to start (Ctrl+O)"))
            self.info_label.setToolTip("")
            return
        h, w = img.shape[:2]
        ch = 1 if img.ndim == 2 else img.shape[2]
        name = os.path.basename(self.state.path or "")
        self.info_label.setText(tr(
            "{name}  |  {width}×{height}  |  {channels} channel(s)  |  step {index}/{last}"
        ).format(name=name, width=w, height=h, channels=ch, index=self.state.index, last=last_step))
        self.info_label.setToolTip(str(self.state.path or ""))
