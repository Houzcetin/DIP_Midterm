"""Non-modal view of the current image's spectrum and frequency filter."""

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from ops.frequency import filter_mask, frequency_filter, spectrum


class FrequencyView(QDialog):
    _TITLES = ("Magnitude spectrum", "Filter mask", "Filtered preview")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Frequency Inspector")
        self.resize(920, 390)
        self.setMinimumSize(580, 260)
        self.figure = Figure(facecolor="#25282d", layout="tight")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.axes = self.figure.subplots(1, 3)

        layout = QVBoxLayout(self)
        layout.addWidget(self.canvas)
        caption = QLabel("Center = low frequencies · Edges = high frequencies")
        caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(caption)

        self._image = None
        self._params = None
        self._spectrum_image = None
        self._magnitude = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(160)
        self._timer.timeout.connect(self._render)
        self._render()

    def update_image(self, img, params):
        """Coalesce updates when the source snapshot or filter settings change."""
        if img is not self._image or params != self._params:
            self._image = img
            self._params = params
            self._timer.start()

    def _render(self):
        img = self._image
        if img is not self._spectrum_image:
            self._magnitude = spectrum(img) if img is not None else None
            self._spectrum_image = img

        images = [None, None, None]
        if img is not None:
            mask = filter_mask(img.shape[:2], **self._params)
            preview = frequency_filter(img, **self._params)
            if preview.ndim == 3:
                preview = preview[..., ::-1]  # Matplotlib displays RGB.
            images = [self._magnitude, mask, preview]

        for ax, title, data, limit in zip(self.axes, self._TITLES, images, (255, 1, 255)):
            ax.clear()
            ax.set_title(title, fontsize=10, color="#e1e6ed")
            ax.set_facecolor("#1e1e1e")
            ax.set(xticks=[], yticks=[])
            for spine in ax.spines.values():
                spine.set_color("#505964")
            if data is not None:
                ax.imshow(data, cmap="gray", vmin=0, vmax=limit)
        if img is None:
            self.axes[1].text(0.5, 0.5, "Open an image to start", ha="center", va="center",
                              color="#c3cad4", transform=self.axes[1].transAxes)
        self.canvas.draw_idle()
