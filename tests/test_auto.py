"""Synthetic inputs exercise the Auto Enhance decisions and their effects."""

import cv2
import numpy as np
import pytest
from PySide6.QtCore import QSettings

from ops.auto import TARGET_BRIGHTNESS, analyze, plan, run
from ops.extras import add_noise, white_balance
from ops.registry import get_op
from ui.main_window import MainWindow


@pytest.fixture
def clean():
    y, x = np.indices((192, 256))
    return np.where((y // 24 + x // 24) % 2, 210, 42).astype(np.uint8)


def make_case(clean, case):
    if case == "dark":
        return (clean * 0.36).astype(np.uint8)
    if case == "bright":
        return (162 + clean * 0.36).astype(np.uint8)
    if case == "low contrast":
        return (103 + clean * 0.16).astype(np.uint8)
    if case == "low local contrast":
        return np.tile(np.arange(24, 232, dtype=np.uint8), (clean.shape[0], 1))
    if case == "impulses":
        return add_noise(clean, "salt_pepper", 0.06, seed=42)
    if case == "severe impulses":
        return add_noise(clean, "salt_pepper", 0.22, seed=42)
    if case == "gaussian":
        return add_noise(clean, "gaussian", 0.06, seed=42)
    if case == "blurred":
        return cv2.GaussianBlur(clean, (25, 25), 4)
    if case == "color cast":
        return np.stack((clean * 0.57, clean * 0.80, clean * 1.17), axis=2).astype(np.uint8)
    return clean


_CASES = (
    ("dark", "gamma"), ("bright", "gamma"), ("low contrast", "contrast_stretch"),
    ("low local contrast", "clahe"), ("impulses", "median"), ("severe impulses", "median"),
    ("gaussian", "bilateral"), ("blurred", "unsharp"), ("color cast", "white_balance"),
)


@pytest.mark.parametrize(("case", "operation"), _CASES)
def test_actions_and_effects(clean, case, operation):
    img = make_case(clean, case)
    result = run(img)
    before, after = result.before, result.after
    steps = [entry.step for entry in result.steps]
    assert steps == plan(before, img)
    step = next((s for s in steps if s.op_id == operation), None)
    assert step is not None
    if operation == "gamma":
        if case == "dark":
            assert step.params["g"] < 1
            assert before.mean_brightness < after.mean_brightness
        else:
            assert step.params["g"] > 1
            assert after.mean_brightness < before.mean_brightness
        assert abs(after.mean_brightness - TARGET_BRIGHTNESS) < abs(
            before.mean_brightness - TARGET_BRIGHTNESS)
    elif operation == "contrast_stretch":
        assert after.dynamic_range > before.dynamic_range
    elif operation == "clahe":
        assert after.local_contrast > before.local_contrast
    elif operation == "median":
        assert steps[0] == step
        assert step.params["k"] == (5 if case == "severe impulses" else 3)
        assert after.salt_pepper_fraction < before.salt_pepper_fraction / 4
    elif operation == "bilateral":
        assert steps[0] == step
        assert after.gaussian_sigma < before.gaussian_sigma / 2
    elif operation == "unsharp":
        assert after.sharpness > before.sharpness
    elif operation == "white_balance":
        assert not before.is_grayscale
        assert after.color_cast < before.color_cast / 4

    for step in steps:
        specs = {p.name: p for p in get_op(step.op_id).params}
        assert step.params.keys() == specs.keys()
        for key, value in step.params.items():
            spec = specs[key]
            assert spec.min <= value <= spec.max
            position = (value - spec.min) / spec.step
            assert position == pytest.approx(round(position))
            if spec.kind == "int" and spec.step == 2:
                assert value % 2 == 1


@pytest.mark.parametrize("bgr", [False, True])
def test_clean_image_stays_unchanged(clean, bgr):
    img = cv2.cvtColor(clean, cv2.COLOR_GRAY2BGR) if bgr else clean
    stats = analyze(img)
    assert stats.is_grayscale
    assert stats.color_cast == stats.saturation_mean == 0
    assert plan(stats, img) == []
    result = run(img)
    assert result.steps == []
    assert result.before == result.after == stats
    dark = run(make_case(img, "dark"))
    assert dark.steps and all(entry.step.op_id != "white_balance" for entry in dark.steps)


def test_white_balance_strength_and_missing_channel(clean):
    img = make_case(clean, "color cast")
    np.testing.assert_array_equal(white_balance(img, 0), img)
    half = white_balance(img, 0.5)
    full = white_balance(img)
    assert analyze(full).color_cast < analyze(half).color_cast < analyze(img).color_cast
    img[:, :, 0] = 0
    assert not white_balance(img)[:, :, 0].any()


def test_stretch_can_resolve_underexposure_before_gamma(clean):
    img = np.where(clean > 126, 70, 40).astype(np.uint8)
    result = run(img)
    assert result.before.mean_brightness < 0.32
    assert [entry.step.op_id for entry in result.steps] == ["contrast_stretch"]
    assert result.after.mean_brightness == pytest.approx(0.5, abs=0.03)


@pytest.mark.parametrize("shape", [(1, 1), (1, 23), (27, 1, 3)])
def test_tiny_constant_images(shape):
    img = np.full(shape, 128, dtype=np.uint8)
    result = run(img)
    assert result.steps == []
    assert result.before.gaussian_sigma == result.before.sharpness == 0


def test_determinism_and_stage_order(clean):
    img = add_noise(make_case(make_case(clean, "color cast"), "dark"), "salt_pepper", 0.10, seed=3)
    original = img.copy()
    img.flags.writeable = False
    a, b = run(img), run(img)
    assert a.before == b.before and a.after == b.after
    assert [entry.step for entry in a.steps] == [entry.step for entry in b.steps]
    assert [entry.step.op_id for entry in a.steps][:2] == ["median", "gamma"]
    previous = img
    for first, second in zip(a.steps, b.steps):
        np.testing.assert_array_equal(first.output, second.output)
        np.testing.assert_array_equal(first.output, get_op(first.step.op_id).func(
            previous, **first.step.params))
        previous = first.output
    assert analyze(previous) == a.after
    np.testing.assert_array_equal(img, original)


def test_controls_report_and_undo(qapp, tmp_path, clean):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings)
    button = window.ops_panel.auto_enhance_button
    action = window.auto_enhance_action
    try:
        assert not button.isEnabled() and not action.isEnabled()
        assert action.shortcut().toString() == "Ctrl+E"
        window.state.load_array(make_case(clean, "dark"), "dark.png")
        window.refresh()
        window.apply_operation("flip", {"mode": "h"})
        source = window.state.current.copy()
        degraded = add_noise(source, "salt_pepper", 0.12, seed=11)
        window.state.apply("Test degradation", degraded)
        window.refresh()
        window.preview_operation("negative", {})
        expected = run(degraded)
        assert len(expected.steps) >= 2
        assert button.isEnabled() and action.isEnabled()
        start_index = window.state.index
        button.click()
        assert window._preview_image is None
        assert window.state.index == start_index + len(expected.steps)
        report = window.auto_report_dialog.text()
        for heading in ("Detected", "Dark image", "Applied steps", "Before → After"):
            assert heading in report
        for index, entry in enumerate(reversed(expected.steps), 1):
            step = entry.step
            label = get_op(step.op_id).label
            assert window.history_panel.currentItem().text().startswith(label)
            assert label in report and step.reason_key.format(**step.reason_args) in report
            assert np.array_equal(window.state.current, entry.output)
            window.undo()
            assert window.state.index == start_index + len(expected.steps) - index
        np.testing.assert_array_equal(window.state.current, degraded)

        window.state.load_array(clean, "clean.png")
        window.refresh()
        action.trigger()
        assert window.state.history_labels() == ["Original"]
        assert "already looks well exposed, clean and sharp" in window.auto_report_dialog.text()
    finally:
        window.close()
        window.deleteLater()


def test_binary_image_gets_no_tone_or_sharpen_steps():
    from core.samples import SAMPLES

    binary = SAMPLES["binary_holes"][2]()
    assert [entry.step.op_id for entry in run(binary).steps] == []


def test_dark_noisy_image_is_restretched_after_tone_fixes():
    from core.samples import SAMPLES

    shapes = SAMPLES["shapes"][2]()
    mask = np.random.default_rng(1).random(shapes.shape[:2])
    damaged = (shapes * 0.35).astype(np.uint8)
    damaged[mask < 0.03], damaged[mask > 0.97] = 0, 255
    result = run(damaged)
    assert [entry.step.op_id for entry in result.steps][-1] == "contrast_stretch"
    assert result.after.dynamic_range > 0.8
    assert 0.32 <= result.after.mean_brightness <= 0.68
