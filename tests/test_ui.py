import numpy as np
import pytest
from PySide6.QtCore import (
    QCoreApplication, QEvent, QMimeData, QPoint, QPointF, QRectF, QSettings, Qt, QUrl,
)
from PySide6.QtGui import QDropEvent, QMouseEvent, QPalette, QWheelEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QGroupBox, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSpinBox,
)

from core.samples import SAMPLES
from ops.frequency import filter_mask, frequency_filter, spectrum
from ops.histogram import compute_hist
from ops.registry import OPERATIONS, get_op
from ui.main_window import MainWindow


@pytest.fixture
def settings(tmp_path):
    return QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def window(qapp, settings):
    window = MainWindow(settings)
    yield window
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture
def loaded_window(window, bgr_png):
    path, _ = bgr_png
    window.state.load(path)
    window.refresh()
    return window


def operation_box(window, op_id):
    op = get_op(op_id)
    toolbox = window.ops_panel.toolbox
    index = next(i for i in range(toolbox.count()) if toolbox.itemText(i) == op.group)
    page = toolbox.widget(index)
    return next(box for box in page.findChildren(QGroupBox) if box.title() == op.label)


def test_load_unicode_path_and_build_registry_pages(loaded_window, bgr_png):
    window = loaded_window
    path, image = bgr_png
    np.testing.assert_array_equal(window.state.original, image)
    assert window.original_view.pixmap() and window.result_view.pixmap()
    status = window.info_label.text()
    for field in (path.name, "64×48", "3 channel(s)", "step 0/0"):
        assert field in status

    toolbox = window.ops_panel.toolbox
    assert [toolbox.itemText(i) for i in range(toolbox.count())] == [
        "A Basics", "B Affine", "C Intensity", "D Spatial Filters",
        "E Histogram", "F Morphology", "Extras", "G Frequency",
    ]
    for index in range(toolbox.count()):
        page = toolbox.widget(index)
        assert isinstance(page, QScrollArea)
        assert [box.title() for box in page.findChildren(QGroupBox)
                if box.title() != "Quick actions"] == [
            op.label for op in OPERATIONS if op.group == toolbox.itemText(index)
        ]


@pytest.mark.parametrize("op", OPERATIONS, ids=lambda op: op.id)
def test_apply_each_operation_with_defaults(loaded_window, op):
    window = loaded_window
    params = {param.name: param.default for param in op.params}
    expected = op.func(window.state.current, **params)
    before = len(window.state.history_labels())
    window.apply_operation(op.id, params)
    assert len(window.state.history_labels()) == before + 1
    assert window.state.history_labels()[-1].startswith(op.label)
    assert window.state.index == 1
    assert not window.result_view.pixmap().isNull()
    np.testing.assert_array_equal(window.state.current, expected)
    assert QApplication.overrideCursor() is None


def test_basics_quick_buttons(loaded_window):
    window = loaded_window
    quick = next(box for box in window.ops_panel.toolbox.widget(0).findChildren(QGroupBox)
                 if box.title() == "Quick actions")
    requests = []
    resets = []
    window.ops_panel.applyRequested.connect(lambda *args: requests.append(args))
    window.ops_panel.resetRequested.connect(lambda: resets.append(True))
    buttons = quick.findChildren(QPushButton)
    assert [button.text() for button in buttons] == [
        "Auto Enhance", "Grayscale", "Flip H", "Flip V", "Rotate 90° CW", "Rotate 90° CCW", "Reset",
    ]
    for button in buttons[1:]:
        button.click()

    assert requests == [
        ("to_grayscale", {}), ("flip", {"mode": "h"}), ("flip", {"mode": "v"}),
        ("rotate90", {"k": 1}), ("rotate90", {"k": -1}),
    ]
    assert resets == [True]
    assert window.state.index == 6
    assert window.state.history_labels()[-1] == "Reset"
    np.testing.assert_array_equal(window.state.current, window.state.original)


def test_numeric_controls_stay_in_sync(loaded_window):
    box = operation_box(loaded_window, "gaussian")
    kernel = box.findChild(QSpinBox)
    sigma = box.findChild(QDoubleSpinBox)
    kernel_slider, sigma_slider = box.findChildren(QSlider)
    kernel.setValue(4)
    assert kernel.value() == 5
    assert kernel_slider.value() == 2
    kernel_slider.setValue(4)
    assert kernel.value() == 9
    sigma_slider.setValue(7)
    assert sigma.value() == 0.7
    sigma.setValue(0.4)
    assert sigma_slider.value() == 4
    kernel_label = next(label for label in box.findChildren(QLabel) if label.text() == "Kernel size")
    assert kernel_label.toolTip() == kernel.toolTip() == kernel_slider.toolTip()
    assert kernel.toolTip()


def test_live_preview_is_debounced_and_apply_commits(loaded_window):
    window = loaded_window
    state = window.state
    original = state.current.copy()
    original_display = window.original_view.pixmap().toImage()
    committed_display = window.result_view.pixmap().toImage()
    requests = []
    window.ops_panel.previewRequested.connect(lambda *args: requests.append(args))
    box = operation_box(window, "flip")
    direction = box.findChild(QComboBox)
    direction.setCurrentText("Vertical")
    direction.setCurrentText("Both")
    assert requests == []
    QTest.qWait(170)

    assert requests == [("flip", {"mode": "both"})]
    assert state.history_labels() == ["Original"]
    np.testing.assert_array_equal(state.current, original)
    assert window.original_view.pixmap().toImage() == original_display
    assert window.result_view.pixmap().toImage() != committed_display
    assert window.statusBar().currentMessage() == "Preview — press Apply to keep"

    box.findChild(QPushButton).click()
    assert state.history_labels() == ["Original", "Flip (mode=both)"]
    assert window.info_label.text().endswith("step 1/1")
    np.testing.assert_array_equal(state.current, original[::-1, ::-1])


def test_page_change_restores_display_and_cancels_pending_preview(loaded_window):
    window = loaded_window
    toolbox = window.ops_panel.toolbox
    direction = operation_box(window, "flip").findChild(QComboBox)
    committed_display = window.result_view.pixmap().toImage()
    requests = []
    cancellations = []
    window.ops_panel.previewRequested.connect(lambda *args: requests.append(args))
    window.ops_panel.previewCancelled.connect(lambda: cancellations.append(True))

    window.preview_operation("flip", {"mode": "v"})
    assert window.result_view.pixmap().toImage() != committed_display
    direction.setCurrentText("Both")
    toolbox.setCurrentIndex(1)
    QTest.qWait(170)
    assert cancellations == [True]
    assert requests == []
    assert window.result_view.pixmap().toImage() == committed_display
    assert window.info_label.text().endswith("step 0/0")


def test_commit_and_undo_cancel_pending_preview(loaded_window):
    window = loaded_window
    direction = operation_box(window, "flip").findChild(QComboBox)
    requests = []
    window.ops_panel.previewRequested.connect(lambda *args: requests.append(args))
    direction.setCurrentText("Vertical")
    window.apply_operation("flip", {"mode": "h"})
    QTest.qWait(170)
    assert requests == []

    direction.setCurrentText("Both")
    window.undo_action.trigger()
    QTest.qWait(170)
    assert requests == []
    assert window.info_label.text().endswith("step 0/1")


def test_edit_actions_follow_history_and_promote_result(loaded_window):
    window = loaded_window
    state = window.state
    original = state.original.copy()
    assert window.reset_action.isEnabled()
    assert not window.undo_action.isEnabled()
    assert not window.redo_action.isEnabled()
    assert not window.promote_action.isEnabled()
    window.apply_operation("to_grayscale", {})
    gray = state.current.copy()
    assert window.undo_action.isEnabled()
    assert window.promote_action.isEnabled()

    window.preview_operation("negative", {})
    window.undo_action.trigger()
    assert window.redo_action.isEnabled()
    assert window.info_label.text().endswith("step 0/1")
    np.testing.assert_array_equal(state.current, original)
    window.redo_action.trigger()
    assert not window.redo_action.isEnabled()
    np.testing.assert_array_equal(state.current, gray)

    window.reset_action.trigger()
    assert state.history_labels() == ["Original", "Grayscale", "Reset"]
    np.testing.assert_array_equal(state.current, original)
    state.goto(1)
    window.refresh()
    assert window.info_label.text().endswith("step 1/2")
    window.promote_action.trigger()
    assert state.history_labels() == ["Original"]
    np.testing.assert_array_equal(state.original, gray)
    assert not window.undo_action.isEnabled()
    assert not window.redo_action.isEnabled()
    assert not window.promote_action.isEnabled()


def test_history_cap_updates_status(loaded_window):
    window = loaded_window
    for _ in range(32):
        window.apply_operation("flip", {"mode": "h"})

    assert len(window.state.history_labels()) == 30
    assert window.state.history_labels()[0] == "Original"
    assert window.info_label.text().endswith("step 29/29")


def test_no_image_skips_preview_and_apply_shows_existing_message(window, monkeypatch):
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args[-1]))
    assert not window.reset_action.isEnabled()
    window.preview_operation("flip", {"mode": "h"})
    assert messages == []
    assert window.result_view.text() == "No image"
    window.apply_operation("flip", {"mode": "h"})
    assert messages == ["Please open an image first."]


def test_failed_non_live_apply_restores_cursor_and_keeps_history(loaded_window, monkeypatch):
    window = loaded_window
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    window.apply_operation("add_noise", {"kind": "invalid", "amount": 0.05, "seed": 0})
    assert len(warnings) == 1
    assert QApplication.overrideCursor() is None
    assert window.state.history_labels() == ["Original"]


def menu_action(window, menu_name, text):
    menu = next(action.menu() for action in window.menuBar().actions()
                if action.text().replace("&", "") == menu_name)
    return next(action for action in menu.actions() if action.text().replace("&", "") == text)


def assert_color_histogram(ax, img):
    for line, counts in zip(ax.lines, compute_hist(img).values()):
        assert line.get_visible()
        np.testing.assert_array_equal(line.get_ydata(), counts)
    assert not ax.patches[0].get_visible()


def test_histograms_follow_load_apply_and_preview(loaded_window):
    window = loaded_window
    original_ax, result_ax = window.histogram_view.axes
    assert_color_histogram(original_ax, window.state.original)
    assert_color_histogram(result_ax, window.state.original)

    window.apply_operation("negative", {})
    committed = window.state.current
    assert_color_histogram(result_ax, committed)
    menu_action(window, "View", "Show Histogram Window…").trigger()
    assert window._histogram_dialog.isVisible()
    assert not window._histogram_dialog.isModal()
    large_ax = window._dialog_histogram.axes[1]
    assert_color_histogram(large_ax, committed)

    window.preview_operation("to_grayscale", {})
    preview = get_op("to_grayscale").func(committed)
    for ax in (result_ax, large_ax):
        assert all(not line.get_visible() for line in ax.lines)
        fill = ax.patches[0]
        assert fill.get_visible()
        np.testing.assert_array_equal(fill.get_xy()[1:257, 1], compute_hist(preview)["gray"])
    assert_color_histogram(original_ax, window.state.original)
    assert window.state.current is committed

    window._clear_preview()
    assert_color_histogram(result_ax, committed)
    assert_color_histogram(large_ax, committed)


def test_history_click_selects_step_and_marks_redo(loaded_window):
    window = loaded_window
    window.apply_operation("negative", {})
    window.apply_operation("to_grayscale", {})
    window.show()
    QApplication.processEvents()
    history = window.history_panel
    assert [history.item(row).text() for row in range(history.count())] == window.state.history_labels()
    assert history.currentRow() == 2

    def click_row(row):
        QTest.mouseClick(history.viewport(), Qt.MouseButton.LeftButton,
                         pos=history.visualItemRect(history.item(row)).center())

    click_row(0)
    assert window.state.index == history.currentRow() == 0
    assert window.info_label.text().endswith("step 0/2")
    disabled = history.palette().brush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text)
    assert history.item(2).foreground() == disabled
    click_row(2)
    assert window.state.index == history.currentRow() == 2
    assert history.item(2).foreground() != disabled
    window.preview_operation("negative", {})
    click_row(2)
    assert window._preview_image is None


def test_zoom_actions_change_both_views_and_restore_fit(window):
    window.open_sample_image()
    window.show()
    QApplication.processEvents()
    views = (window.original_view, window.result_view)
    fit = tuple(view.zoom_factor for view in views)
    menu_action(window, "View", "Zoom In").trigger()
    assert tuple(view.zoom_factor for view in views) == pytest.approx(tuple(f * 1.25 for f in fit))
    menu_action(window, "View", "Zoom Out").trigger()
    assert tuple(view.zoom_factor for view in views) == pytest.approx(fit)
    menu_action(window, "View", "Actual Size 100%").trigger()
    assert all(view.zoom_factor == 1.0 for view in views)
    menu_action(window, "View", "Fit to Window").trigger()
    assert tuple(view.zoom_factor for view in views) == pytest.approx(fit)


def test_wheel_anchors_pixel_and_pan_links_relative_centers(window):
    window.open_sample_image()
    window.apply_operation("scale", {"sx": 2.0, "sy": 2.0, "interp": "nearest"})
    window.show()
    QApplication.processEvents()
    original, result = window.original_view, window.result_view
    menu_action(window, "View", "Zoom In").trigger()
    point = original.rect().center() + QPoint(35, 0)
    pixel_before = original.pixel_at(QPointF(point))
    wheel = QWheelEvent(QPointF(point), QPointF(original.mapToGlobal(point)), QPoint(),
                        QPoint(0, 120), Qt.MouseButton.NoButton,
                        Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(original, wheel)
    assert original.pixel_at(QPointF(point)) == pixel_before
    assert original.zoom_factor == pytest.approx(2 * result.zoom_factor, rel=0.02)

    center = original.rect().center()
    QTest.mousePress(original, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(original, center - QPoint(40, 0))
    QTest.mouseRelease(original, Qt.MouseButton.LeftButton)
    x_original, _, _ = original.pixel_at(QPointF(center))
    x_result, _, _ = result.pixel_at(QPointF(result.rect().center()))
    assert x_original > window.state.original.shape[1] / 2
    assert abs(x_original * 2 - x_result) <= 2

    QTest.mouseDClick(original, Qt.MouseButton.LeftButton, pos=center)
    assert original.zoom_factor * window.state.original.shape[1] == pytest.approx(original.width())
    assert result.zoom_factor * window.state.current.shape[1] == pytest.approx(result.width())
    menu_action(window, "View", "Actual Size 100%").trigger()
    for _ in range(12):
        menu_action(window, "View", "Zoom In").trigger()
    assert original.zoom_factor == result.zoom_factor == 8.0


def test_pixel_inspector_emits_bgr_and_shows_rgb_in_status(loaded_window):
    window = loaded_window
    window.show()
    QApplication.processEvents()
    view = window.original_view
    view.actual_size()
    image = window.state.original
    x, y = 5, 7
    pos = QPointF((view.width() - image.shape[1]) / 2 + x + 0.5,
                  (view.height() - image.shape[0]) / 2 + y + 0.5)
    b, g, r = map(int, image[y, x])
    assert view.pixel_at(pos) == (x, y, (b, g, r))
    assert view.pixel_at(QPointF(0, 0)) is None

    pixels = []
    view.pixelHovered.connect(lambda *pixel: pixels.append(pixel))
    event = QMouseEvent(QEvent.Type.MouseMove, pos, QPointF(view.mapToGlobal(pos.toPoint())),
                        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(view, event)
    assert pixels == [(x, y, (b, g, r))]
    assert window.statusBar().currentMessage() == f"x={x}, y={y} | R,G,B={r},{g},{b}"

    window.preview_operation("to_grayscale", {})
    gray_view = window.result_view
    gray_pos = QPointF((gray_view.width() - image.shape[1]) / 2 + x + 0.5,
                       (gray_view.height() - image.shape[0]) / 2 + y + 0.5)
    assert gray_view.pixel_at(gray_pos) == (x, y, int(window._preview_image[y, x]))


def test_drop_opens_local_file(window, bgr_png):
    path, image = bgr_png
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    drop = QDropEvent(QPointF(10, 10), Qt.DropAction.CopyAction, mime,
                      Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert window.acceptDrops()
    window.dropEvent(drop)
    assert drop.isAccepted()
    np.testing.assert_array_equal(window.state.current, image)
    assert window.recent_menu.actions()[0].toolTip() == str(path)


def test_drop_invalid_image_uses_open_error_dialog(loaded_window, tmp_path, monkeypatch):
    window = loaded_window
    original = window.state.current
    errors = []
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: errors.append(args[-1]))
    path = tmp_path / "invalid.png"
    path.write_bytes(b"invalid image")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(path))])
    drop = QDropEvent(QPointF(), Qt.DropAction.CopyAction, mime,
                      Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    window.dropEvent(drop)
    assert len(errors) == 1
    assert window.state.current is original
    assert not window.recent_menu.actions()


@pytest.mark.parametrize("name", SAMPLES)
def test_sample_actions_load_in_memory_images(window, name):
    label, suggestion, generate = SAMPLES[name]
    menu = menu_action(window, "File", "Sample Images").menu()
    assert menu.toolTipsVisible()
    action = next(action for action in menu.actions() if action.text().replace("&&", "&") == label)
    assert action.toolTip() == suggestion
    action.trigger()
    assert window.state.path == f"sample_{name}.png"
    np.testing.assert_array_equal(window.state.current, generate())
    assert window.state.history_labels() == ["Original"]
    assert window.state.path in window.info_label.text()
    assert window.statusBar().currentMessage() == suggestion
    assert not window.recent_menu.actions()


def test_recent_files_are_capped_reordered_and_persisted(window, settings, bgr_png, monkeypatch):
    path, _ = bgr_png
    paths = [path.with_name(f"Image {index}.png") for index in range(6)]
    open_action = menu_action(window, "File", "Open...")
    for entry in paths:
        entry.write_bytes(path.read_bytes())
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(entry), ""))
        open_action.trigger()
    assert [action.toolTip() for action in window.recent_menu.actions()] == list(map(str, paths[:0:-1]))
    window.recent_menu.actions()[-1].trigger()
    expected = [paths[1], *paths[:1:-1]]
    assert window.state.path == str(paths[1])
    settings.sync()
    stored_settings = QSettings(settings.fileName(), QSettings.Format.IniFormat)
    reopened = MainWindow(stored_settings)
    try:
        assert [action.toolTip() for action in reopened.recent_menu.actions()] == list(map(str, expected))
    finally:
        reopened.close()
        reopened.deleteLater()


def test_compare_shortcut_toggles_original_and_restores_preview(loaded_window):
    window = loaded_window
    window.apply_operation("negative", {})
    window.preview_operation("to_grayscale", {})
    preview = window.result_view.pixmap().toImage()
    window.show()
    window.activateWindow()
    QApplication.processEvents()
    QTest.keyClick(window.result_view, Qt.Key.Key_B, Qt.KeyboardModifier.ControlModifier)
    assert window.wipe_action.isChecked()
    QTest.keyClick(window.result_view, Qt.Key.Key_Space)
    assert window.compare_action.isChecked()
    assert window.wipe_action.isChecked()
    assert window.result_view._compare_pixmap is None
    assert window.result_view.pixmap().toImage() == window.original_view.pixmap().toImage()
    assert_color_histogram(window.histogram_view.axes[1], window.state.original)
    editor = operation_box(window, "rotate90").findChild(QSpinBox)
    editor.setFocus()
    QTest.keyClick(editor, Qt.Key.Key_Space)
    assert not window.compare_action.isChecked()
    assert window.result_view._compare_pixmap is not None
    assert window.result_view.pixmap().toImage() == preview
    assert window.state.index == 1


def test_wipe_paints_stretched_original_alongside_preview(window):
    image = np.full((40, 80), 50, dtype=np.uint8)
    image[20:] = 100
    window.state.load_array(image, "wipe.png")
    window.refresh()
    window.show()
    QApplication.processEvents()
    window.apply_operation("negative", {})
    window.wipe_action.trigger()
    window.preview_operation("rotate90", {"k": 1})
    hint = "sizes differ — original stretched"
    assert window.statusBar().currentMessage() == hint

    view = window.result_view
    rect = view._image_rect()
    grabbed = view.grab().toImage()
    for x_fraction, expected in ((0.25, 100), (0.75, 205)):
        point = QPointF(rect.left() + x_fraction * rect.width(),
                        rect.top() + 0.75 * rect.height())
        assert grabbed.pixelColor(point.toPoint()).red() == expected
        assert view.pixel_at(point)[2] == expected

    window.statusBar().clearMessage()
    window.preview_operation("rotate90", {"k": -1})
    assert window.statusBar().currentMessage() != hint


def test_wipe_divider_drags_and_keeps_fraction_across_zoom_and_resize(window):
    window.open_sample_image()
    window.show()
    QApplication.processEvents()
    window.wipe_action.trigger()
    view = window.result_view
    assert view.split_fraction == 0.5
    rect = view._image_rect().intersected(QRectF(view.rect()))
    start = QPoint(round(rect.center().x()) + 6, round(rect.top() + rect.height() / 4))
    end = start + QPoint(round(rect.width() / 4), 0)

    QTest.mouseMove(view, start)
    assert view.cursor().shape() == Qt.CursorShape.SplitHCursor
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view, end)
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=end)
    fraction = view.split_fraction
    assert fraction == pytest.approx(0.75, abs=0.005)

    view.zoom_in()
    window.resize(window.width() + 100, window.height() + 60)
    QApplication.processEvents()
    assert view.split_fraction == fraction
    view.actual_size()
    view.zoom_in()
    center = view.rect().center()
    before = view.pixel_at(QPointF(center))
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=center)
    QTest.mouseMove(view, center - QPoint(35, 0))
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=center - QPoint(35, 0))
    assert view.pixel_at(QPointF(center))[0] > before[0]
    assert view.split_fraction == fraction


def test_frequency_inspector_follows_committed_result_and_debounced_params(loaded_window):
    window = loaded_window
    action = menu_action(window, "View", "Frequency Inspector…")
    assert action.shortcut().toString() == "Ctrl+F"
    action.trigger()
    dialog = window._frequency_dialog
    assert dialog.isVisible() and not dialog.isModal()

    def plotted_images():
        return [ax.images[0].get_array() for ax in dialog.axes]

    QTest.qWait(215)
    image = window.state.current
    original_spectrum, original_mask, _ = plotted_images()
    np.testing.assert_array_equal(original_spectrum, spectrum(image))

    box = operation_box(window, "frequency_filter")
    kind, shape = box.findChildren(QComboBox)
    kind.setCurrentText("Band-stop")
    shape.setCurrentText("Gaussian")
    cutoff = box.findChildren(QDoubleSpinBox)[0]
    cutoff.setValue(8)
    params = window.ops_panel.current_params("frequency_filter")
    assert (params["kind"], params["shape"], params["cutoff"]) == ("bandstop", "gaussian", 8)
    assert plotted_images()[1] is original_mask
    QTest.qWait(215)

    magnitude, mask, preview = plotted_images()
    np.testing.assert_array_equal(magnitude, spectrum(image))
    np.testing.assert_array_equal(mask, filter_mask(image.shape[:2], **params))
    np.testing.assert_array_equal(preview, frequency_filter(image, **params)[..., ::-1])
    assert window.state.current is image

    window.apply_operation("rotate90", {"k": 1})
    QTest.qWait(215)
    np.testing.assert_array_equal(plotted_images()[0], spectrum(window.state.current))


def test_dock_toggle_actions_and_help_menu(window, monkeypatch):
    window.show()
    for dock in (window.operations_dock, window.histogram_dock, window.history_dock):
        action = menu_action(window, "View", dock.windowTitle())
        assert action == dock.toggleViewAction()
        action.trigger()
        assert dock.isHidden()
        action.trigger()
        assert dock.isVisible()

    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args[-1]))
    monkeypatch.setattr(QMessageBox, "about", lambda *args: messages.append(args[-1]))
    menu_action(window, "Help", "Keyboard Shortcuts").trigger()
    for shortcut in ("Ctrl+O", "Ctrl+S", "Ctrl+Z", "Ctrl+Y", "Ctrl+Shift+Z", "Ctrl+R",
                     "Ctrl+0", "Ctrl+1", "Ctrl+=", "Ctrl+-", "Space", "Ctrl+B", "Ctrl+F"):
        assert shortcut in messages[0]
    menu_action(window, "Help", "About").trigger()
    assert all(part in messages[1] for part in ("COMP 4360 Midterm", "PySide6", "OpenCV"))


def test_friendly_choice_label_emits_raw_value(loaded_window):
    window = loaded_window
    box = operation_box(window, "flip")
    combo = box.findChild(QComboBox)
    requests = []
    window.ops_panel.applyRequested.connect(lambda *args: requests.append(args))
    assert combo.currentText() == "Horizontal"
    assert combo.currentData() == "h"
    box.findChild(QPushButton).click()
    assert requests == [("flip", {"mode": "h"})]


def test_panel_splitter_resizes_and_double_click_equalizes(window):
    splitter = window.panel_splitter
    splitter.resize(1000, 400)
    splitter.setSizes([700, 300])
    left, right = splitter.sizes()
    assert left > right
    assert not splitter.childrenCollapsible()

    handle = splitter.handle(1)
    event = QMouseEvent(QEvent.Type.MouseButtonDblClick, QPointF(2, 2), QPointF(2, 2),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(handle, event)
    left, right = splitter.sizes()
    assert abs(left - right) <= 1
