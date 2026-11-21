import numpy as np
import pytest

from core.state import ImageState


@pytest.fixture
def state(bgr_png):
    path, _ = bgr_png
    state = ImageState()
    state.load(path)
    return state


def test_empty_history():
    state = ImageState()
    state.undo()
    state.redo()
    state.goto(0)
    state.reset()
    state.set_result_as_original()
    assert state.current is None
    assert state.index == -1
    assert state.history_labels() == []
    assert not state.can_undo()
    assert not state.can_redo()


def test_history_navigation_and_redo_truncation(state):
    first = np.full((3, 2), 40, dtype=np.uint8)
    second = np.full((3, 2), 80, dtype=np.uint8)
    assert state.history_labels() == ["Original"]
    assert state.index == 0
    state.apply("First", first)
    state.apply("Second", second)
    assert state.index == 2
    assert not state.can_redo()

    state.undo()
    assert state.index == 1
    assert state.can_undo() and state.can_redo()
    np.testing.assert_array_equal(state.current, first)
    state.redo()
    np.testing.assert_array_equal(state.current, second)
    state.goto(0)
    state.goto(-1)
    state.goto(3)
    assert state.index == 0
    assert not state.can_undo()
    np.testing.assert_array_equal(state.current, state.original)

    state.apply("Branch", second)
    second.fill(0)
    assert state.history_labels() == ["Original", "Branch"]
    assert state.index == 1
    assert not state.can_redo()
    np.testing.assert_array_equal(state.current, np.full((3, 2), 80))


def test_reset_is_undoable_and_uses_the_promoted_original(state):
    result = np.full((4, 5), 120, dtype=np.uint8)
    source_path = state.path
    state.apply("Result", result)
    state.reset()
    assert state.history_labels() == ["Original", "Result", "Reset"]
    np.testing.assert_array_equal(state.current, state.original)
    state.undo()
    np.testing.assert_array_equal(state.current, result)

    state.set_result_as_original()
    assert state.path == source_path
    assert state.index == 0
    assert state.history_labels() == ["Original"]
    assert not state.can_undo() and not state.can_redo()
    np.testing.assert_array_equal(state.original, result)
    state.apply("Another", np.zeros_like(result))
    state.reset()
    np.testing.assert_array_equal(state.current, result)


def test_history_cap_preserves_original(state):
    original = state.original.copy()
    for i in range(35):
        state.apply(f"Step {i + 1}", np.full((2, 2), i + 1, dtype=np.uint8))

    assert state.history_labels() == ["Original", *(f"Step {i}" for i in range(7, 36))]
    assert state.index == 29
    np.testing.assert_array_equal(state.current, np.full((2, 2), 35))
    state.goto(1)
    np.testing.assert_array_equal(state.current, np.full((2, 2), 7))
    state.undo()
    np.testing.assert_array_equal(state.current, original)


def test_save_active_step_and_reload_clears_history(state, bgr_png):
    source_path, original = bgr_png
    state.apply("Black", np.zeros_like(original))
    state.undo()
    path = source_path.with_name("çıktı.png")
    state.save(path)
    state.load(path)
    assert state.path == path
    assert state.history_labels() == ["Original"]
    assert state.index == 0
    assert not state.can_redo()
    np.testing.assert_array_equal(state.current, original)
