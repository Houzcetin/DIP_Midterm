"""Show the original and displayed result intensity distributions."""

import matplotlib
import numpy as np
from PySide6.QtWidgets import QVBoxLayout, QWidget

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from matplotlib.ticker import MaxNLocator

from ops.histogram import compute_hist
from ui.i18n import tr
from ui.themes import Theme, get_theme


class HistogramView(QWidget):
    _BINS = np.arange(256)
    _COLORS = {"b": "#559bff", "g": "#6bd887", "r": "#ff6979"}

    def __init__(self, parent=None, *, theme: Theme | None = None):
        super().__init__(parent)
        self.setMinimumSize(245, 280)
        self.figure = Figure(figsize=(3, 4), layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.subplots(2, 1)
        self._images = [None, None]
        self._histograms = [{}, {}]
        self._artists = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        for ax in self.axes:
            # Pad x so spikes at 0 and 255 (e.g. binary images) are not hidden by the spines.
            ax.set(xlim=(-4, 259), ylim=(0, 1), xticks=[0, 64, 128, 192, 255])
            ax.tick_params(labelsize=8, length=3)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
            ax.yaxis.get_offset_text().set_fontsize(8)
            ax.grid(axis="y", linewidth=0.5)
            ax.set_axisbelow(True)

            fill = Polygon([[0, 0], [255, 0]], linewidth=0.6, alpha=0.7, visible=False)
            ax.add_patch(fill)
            lines = {channel: ax.plot(self._BINS, np.zeros(256), color=color,
                                      linewidth=1, alpha=0.75, visible=False)[0]
                     for channel, color in self._COLORS.items()}
            self._artists.append((fill, lines))
        self.retranslate()
        self.apply_theme(theme or get_theme(None))

    def retranslate(self):
        for ax, title in zip(self.axes, ("Original", "Result")):
            ax.set_title(tr(title), fontsize=10)
            ax.set_ylabel(tr("Pixel count"), fontsize=8)
        self.axes[-1].set_xlabel(tr("Intensity"), fontsize=8)
        self.canvas.draw_idle()

    def apply_theme(self, theme: Theme) -> None:
        """Recolor the histogram chrome and grayscale fill in place."""
        self.figure.set_facecolor(theme.window)
        for ax, (fill, _) in zip(self.axes, self._artists):
            ax.set_facecolor(theme.base)
            ax.title.set_color(theme.text)
            ax.xaxis.label.set_color(theme.muted_text)
            ax.yaxis.label.set_color(theme.muted_text)
            ax.tick_params(colors=theme.muted_text, grid_color=theme.button)
            for spine in ax.spines.values():
                spine.set_color(theme.border)
            fill.set_facecolor(theme.accent)
            fill.set_edgecolor(theme.accent)
        self.canvas.draw_idle()

    def update_images(self, original, result):
        """Refresh changed snapshots and coalesce the canvas repaint."""
        changed = False
        for index, image in enumerate((original, result)):
            if image is self._images[index]:
                continue
            other = 1 - index
            if image is None:
                counts = {}
            elif image is self._images[other]:
                counts = self._histograms[other]
            else:
                counts = compute_hist(image)
            self._images[index] = image
            self._histograms[index] = counts
            self._set_counts(index, counts)
            changed = True
        if changed:
            self.canvas.draw_idle()

    def _set_counts(self, index, counts):
        fill, lines = self._artists[index]
        gray = counts.get("gray")
        fill.set_visible(gray is not None)
        if gray is not None:
            fill.set_xy(np.column_stack((np.r_[0, self._BINS, 255], np.r_[0, gray, 0])))
        for channel, line in lines.items():
            line.set_visible(channel in counts)
            if channel in counts:
                line.set_ydata(counts[channel])
        peak = max((series.max() for series in counts.values()), default=0)
        self.axes[index].set_ylim(0, max(1, peak * 1.05))
