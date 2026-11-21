import numpy as np
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QGroupBox, QLabel, QMessageBox,
    QPushButton, QScrollArea, QSlider, QSpinBox,
)

from ops.registry import OPERATIONS, get_op
from ui.main_window import MainWindow


@pytest.fixture
def window(qapp):
    window = MainWindow()
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
        "E Histogram", "F Morphology", "Extras",
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
        "Grayscale", "Flip H", "Flip V", "Rotate 90° CW", "Rotate 90° CCW", "Reset",
    ]
    for button in buttons:
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
    direction.setCurrentText("v")
    direction.setCurrentText("both")
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
    direction.setCurrentText("both")
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
    direction.setCurrentText("v")
    window.apply_operation("flip", {"mode": "h"})
    QTest.qWait(170)
    assert requests == []

    direction.setCurrentText("both")
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
