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


class HistogramView(QWidget):
    _BINS = np.arange(256)
    _COLORS = {"b": "#559bff", "g": "#6bd887", "r": "#ff6979"}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(245, 280)
        self.figure = Figure(figsize=(3, 4), facecolor="#25282d", layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.subplots(2, 1)
        self._images = [None, None]
        self._histograms = [{}, {}]
        self._artists = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        for ax, title in zip(self.axes, ("Original", "Result")):
            ax.set_title(title, fontsize=10, color="#e1e6ed")
            ax.set_facecolor("#1e1e1e")
            # Pad x so spikes at 0 and 255 (e.g. binary images) are not hidden by the spines.
            ax.set(xlim=(-4, 259), ylim=(0, 1), xticks=[0, 64, 128, 192, 255])
            ax.tick_params(colors="#c3cad4", labelsize=8, length=3)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=3, integer=True))
            ax.yaxis.get_offset_text().set(color="#c3cad4", fontsize=8)
            for spine in ax.spines.values():
                spine.set_color("#505964")
            ax.grid(axis="y", color="#393e45", linewidth=0.5)
            ax.set_axisbelow(True)

            fill = Polygon([[0, 0], [255, 0]], facecolor="#c3cad4", edgecolor="#c3cad4",
                           linewidth=0.6, alpha=0.7, visible=False)
            ax.add_patch(fill)
            lines = {channel: ax.plot(self._BINS, np.zeros(256), color=color,
                                      linewidth=1, alpha=0.75, visible=False)[0]
                     for channel, color in self._COLORS.items()}
            self._artists.append((fill, lines))

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
