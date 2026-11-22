"""Display the measurements and reasoning from Auto Enhance."""

from collections.abc import Callable
from html import escape

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout, QWidget

from ops.auto import AutoResult, BRIGHT_THRESHOLD, DARK_THRESHOLD, ImageStats, Step
from ops.registry import get_op
from ui.i18n import tr


_METRICS = (
    ("mean_brightness", "Mean brightness", ".2f"),
    ("contrast", "Overall contrast", ".3f"),
    ("dynamic_range", "Luminance range (2nd–98th percentile)", ".2f"),
    ("local_contrast", "Local contrast", ".3f"),
    ("salt_pepper_fraction", "Isolated black and white pixels", ".1%"),
    ("gaussian_sigma", "Estimated Gaussian noise (8-bit sigma)", ".1f"),
    ("sharpness", "Sharpness (Laplacian variance)", ".5f"),
    ("color_cast", "Color cast (channel mean deviation)", ".3f"),
    ("saturation_mean", "Mean saturation", ".2f"),
)


class AutoReportDialog(QDialog):
    """Show a selectable report and retranslate it when the language changes."""

    def __init__(self, parent: QWidget, format_operation: Callable[[str, dict], str]):
        super().__init__(parent)
        self._format_operation = format_operation
        self._summary: tuple[ImageStats, list[Step], ImageStats] | None = None
        self._report = QTextBrowser()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.close)
        self._close_button = buttons.button(QDialogButtonBox.StandardButton.Close)
        layout = QVBoxLayout(self)
        layout.addWidget(self._report)
        layout.addWidget(buttons)
        self.resize(660, 580)

    def set_result(self, result: AutoResult) -> None:
        self._summary = result.before, [entry.step for entry in result.steps], result.after
        self.retranslate()

    def text(self) -> str:
        return self._report.toPlainText()

    def retranslate(self) -> None:
        self.setWindowTitle(tr("Auto Enhance Report"))
        self._close_button.setText(tr("Close"))
        if self._summary is None:
            return
        before, applied_steps, after = self._summary
        exposure = "Well-exposed image"
        if before.mean_brightness < DARK_THRESHOLD:
            exposure = "Dark image"
        elif before.mean_brightness > BRIGHT_THRESHOLD:
            exposure = "Bright image"
        detected = [tr(exposure), tr("Grayscale image" if before.is_grayscale else "Color image")]
        rows = []
        for field, label, precision in _METRICS:
            previous = format(getattr(before, field), precision)
            current = format(getattr(after, field), precision)
            value = escape(previous) if previous == current else f"{escape(previous)} → <b>{escape(current)}</b>"
            rows.append(f"<tr><td>{escape(tr(label))}</td><td align='right'>{value}</td></tr>")

        steps = []
        for step in applied_steps:
            operation = self._format_operation(get_op(step.op_id).label, step.params)
            reason = tr(step.reason_key).format(**step.reason_args)
            steps.append(f"<li><b>{escape(operation)}</b><br>{escape(reason)}</li>")
        steps_html = (f"<ol>{''.join(steps)}</ol>" if steps else
                      f"<p>{escape(tr('The image already looks well exposed, clean and sharp.'))}</p>")

        self._report.setHtml(
            f"<h3>{escape(tr('Detected'))}</h3><p>{escape(' · '.join(detected))}</p>"
            f"<h3>{escape(tr('Applied steps'))}</h3>{steps_html}"
            f"<h3>{escape(tr('Before → After'))}</h3>"
            f"<table cellspacing='0' cellpadding='3' width='100%'>{''.join(rows)}</table>")
