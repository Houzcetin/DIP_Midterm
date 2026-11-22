"""The exe self-test path (`DIP_Midterm.exe --selftest DIR`) must pass from source too."""

import re

from main import run_selftest
from ops.registry import OPERATIONS


def test_selftest_runs_every_operation(qapp, tmp_path):
    assert run_selftest(qapp, tmp_path) == 0
    report = (tmp_path / "selftest.txt").read_text(encoding="utf-8")
    assert report.startswith(f"OK {len(OPERATIONS)} operations")
    assert "themes=6" in report
    assert "languages=2" in report
    assert "avatars=6" in report
    assert re.search(r"\bauto_steps=[1-9]\d*\b", report)
    assert (tmp_path / "selftest.png").stat().st_size > 0
