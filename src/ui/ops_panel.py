"""Build the operations dock controls from registry metadata."""

from decimal import Decimal
from math import floor

from PySide6.QtCore import QSignalBlocker, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QSlider, QSpinBox,
    QToolBox, QVBoxLayout, QWidget,
)

from ops.registry import OPERATIONS, OperationSpec, ParamSpec


GROUPS = (
    "A Basics", "B Affine", "C Intensity", "D Spatial Filters",
    "E Histogram", "F Morphology", "Extras",
)

CHOICE_LABELS = {
    "h": "Horizontal",
    "v": "Vertical",
    "global": "Global (t)",
    "otsu": "Otsu (auto)",
    "salt_pepper": "Salt & pepper",
}


class OpsPanel(QWidget):
    """Expose the operation forms and their preview and apply signals."""

    previewRequested = Signal(str, dict)
    applyRequested = Signal(str, dict)
    previewCancelled = Signal()
    resetRequested = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumWidth(300)

        self._pending_preview = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._emit_preview)

        self.toolbox = QToolBox()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbox)
        for group in GROUPS:
            self.toolbox.addItem(self._group_page(group), group)
        self.toolbox.currentChanged.connect(self._page_changed)

    def _group_page(self, group):
        page = QWidget()
        layout = QVBoxLayout(page)
        if group == "A Basics":
            layout.addWidget(self._quick_actions())
        for op in OPERATIONS:
            if op.group == group:
                layout.addWidget(self._operation_box(op))
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(page)
        return scroll

    def _quick_actions(self):
        box = QGroupBox("Quick actions")
        grid = QGridLayout(box)
        for i, (label, op_id, params) in enumerate((
            ("Grayscale", "to_grayscale", {}),
            ("Flip H", "flip", {"mode": "h"}),
            ("Flip V", "flip", {"mode": "v"}),
            ("Rotate 90° CW", "rotate90", {"k": 1}),
            ("Rotate 90° CCW", "rotate90", {"k": -1}),
        )):
            button = QPushButton(label)
            button.clicked.connect(
                lambda checked=False, op_id=op_id, params=params:
                self.applyRequested.emit(op_id, params)
            )
            grid.addWidget(button, i // 3, i % 3)
        reset = QPushButton("Reset")
        reset.setToolTip("Return to the original image (undoable, Ctrl+R).")
        reset.clicked.connect(self.resetRequested.emit)
        grid.addWidget(reset, 1, 2)
        return box

    def _operation_box(self, op: OperationSpec):
        box = QGroupBox(op.label)
        layout = QVBoxLayout(box)
        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        layout.addLayout(form)
        readers = {}

        def read_params():
            return {name: read() for name, read in readers.items()}

        def schedule_preview(*_):
            self._pending_preview = (op.id, read_params())
            self._preview_timer.start()

        for param in op.params:
            control, read, changed = self._parameter_control(param)
            label = QLabel(param.label)
            label.setToolTip(param.tooltip)
            control.setToolTip(param.tooltip)
            form.addRow(label, control)
            readers[param.name] = read
            if op.live:
                changed.connect(schedule_preview)

        apply = QPushButton("Apply")
        apply.clicked.connect(lambda: self.applyRequested.emit(op.id, read_params()))
        layout.addWidget(apply, alignment=Qt.AlignmentFlag.AlignRight)
        return box

    def _parameter_control(self, param: ParamSpec):
        if param.kind == "choice":
            combo = QComboBox()
            for value in param.choices:
                combo.addItem(CHOICE_LABELS.get(value, value.capitalize()), value)
            combo.setCurrentIndex(combo.findData(param.default))
            return combo, combo.currentData, combo.currentIndexChanged
        if param.kind == "bool":
            check = QCheckBox()
            check.setChecked(param.default)
            return check, check.isChecked, check.toggled
        return self._numeric_control(param)

    def _numeric_control(self, param: ParamSpec):
        minimum, maximum, step = param.min, param.max, param.step
        if param.kind == "int":
            spin = QSpinBox()
        else:
            spin = QDoubleSpinBox()
            decimals = max(-Decimal(str(value)).normalize().as_tuple().exponent
                           for value in (minimum, maximum, step))
            spin.setDecimals(max(1, decimals))
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setKeyboardTracking(False)
        spin.setToolTip(param.tooltip)

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, round((maximum - minimum) / step))
        slider.setToolTip(param.tooltip)

        def sync_slider(value):
            # Anchor the grid to the minimum so odd kernels stay odd.
            position = floor((value - minimum) / step + 0.5)
            with QSignalBlocker(spin), QSignalBlocker(slider):
                spin.setValue(minimum + position * step)
                slider.setValue(position)

        spin.setValue(param.default)
        sync_slider(spin.value())
        spin.valueChanged.connect(sync_slider)
        slider.valueChanged.connect(lambda position: spin.setValue(minimum + position * step))

        control = QWidget()
        layout = QHBoxLayout(control)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(spin)
        layout.addWidget(slider, stretch=1)
        return control, spin.value, spin.valueChanged

    def cancel_pending_preview(self):
        self._preview_timer.stop()
        self._pending_preview = None

    def _emit_preview(self):
        pending = self._pending_preview
        self._pending_preview = None
        if pending is not None:
            self.previewRequested.emit(*pending)

    def _page_changed(self):
        self.cancel_pending_preview()
        self.previewCancelled.emit()
