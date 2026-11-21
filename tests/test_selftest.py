"""The exe self-test path (`DIP_Midterm.exe --selftest DIR`) must pass from source too."""

from main import run_selftest
from ops.registry import OPERATIONS


def test_selftest_runs_every_operation(qapp, tmp_path):
    assert run_selftest(qapp, tmp_path) == 0
    report = (tmp_path / "selftest.txt").read_text(encoding="utf-8")
    assert report.startswith(f"OK {len(OPERATIONS)} operations")
    assert (tmp_path / "selftest.png").stat().st_size > 0
