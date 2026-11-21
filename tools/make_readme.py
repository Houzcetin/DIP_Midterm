"""Capture the app and generate the two-page submission README with Qt."""

import os
import sys
from datetime import date
from html import escape
from pathlib import Path
from tempfile import TemporaryDirectory

from PySide6.QtCore import QMarginsF, QPoint, QPointF, QRectF, QSettings, Qt, QUrl
from PySide6.QtGui import (
    QColor, QFont, QFontDatabase, QPageLayout, QPageSize, QPainter, QPdfWriter,
    QPen, QTextDocument,
)
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from main import MainWindow, configure_appearance
from ops.registry import OPERATIONS


def capture_ui(app):
    with TemporaryDirectory(prefix="dip-settings-") as folder:
        settings = QSettings(str(Path(folder) / "readme.ini"), QSettings.Format.IniFormat)
        window = MainWindow(settings=settings)
        window.resize(1500, 850)
        window.show()
        app.processEvents()
        window.open_sample_image()
        toolbox = window.ops_panel.toolbox
        toolbox.setCurrentIndex(next(i for i in range(toolbox.count())
                                     if toolbox.itemText(i) == "D Spatial Filters"))
        window.apply_operation("gaussian", {"k": 5})
        window.apply_operation("equalize", {})
        window.wipe_action.setChecked(True)
        app.processEvents()

        view = window.original_view
        pixel = view.pixel_at(QPointF(view.rect().center()))
        if pixel is not None:
            view.pixelHovered.emit(*pixel)
        screenshot = window.grab()

        status = window.statusBar()
        badges = (
            (window.operations_dock, QPoint(window.operations_dock.width() - 34, 48)),
            (view, QPoint(view.width() - 29, 30)),
            (window.result_view, QPoint(window.result_view.width() - 29, 30)),
            (window.histogram_dock, QPoint(window.histogram_dock.width() - 32, 47)),
            (window.history_dock, QPoint(window.history_dock.width() - 32, 48)),
            (status, QPoint(205, 0)),
        )
        annotated = screenshot.copy()
        with QPainter(annotated) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            font = QFont("Segoe UI")
            font.setPixelSize(24)
            font.setBold(True)
            painter.setFont(font)
            for number, (widget, anchor) in enumerate(badges, start=1):
                center = widget.mapTo(window, anchor)
                circle = QRectF(center.x() - 19, center.y() - 19, 38, 38)
                painter.setPen(QPen(QColor("#ffffff"), 2.5))
                painter.setBrush(QColor("#1554a2"))
                painter.drawEllipse(circle)
                painter.drawText(circle, Qt.AlignmentFlag.AlignCenter, str(number))

        docs = ROOT / "docs"
        docs.mkdir(exist_ok=True)
        for image, name in ((screenshot, "ui.png"), (annotated, "ui_map.png")):
            if not image.save(str(docs / name), "PNG"):
                raise RuntimeError(f"Could not save {docs / name}")
        window.close()
        return annotated.toImage()


def checklist_cell(title, items):
    lines = "<br>".join(f'<span class="check">✔</span> {escape(item)}' for item in items)
    heading = f"<b>{title}</b><br>" if title else ""
    return f'<td width="50%" bgcolor="#f2f6fb">{heading}{lines}</td>'


def feature_checklist():
    groups = (
        ("A Basics", ("Grayscale, horizontal and vertical flip", "90° rotations, reset to original")),
        ("B Affine", ("Rotation with angle input, uniform or X/Y scaling",
                      "Translate dx/dy, shear X/Y/both")),
        ("C Intensity", ("Contrast stretching, gamma slider, negative",)),
        ("D Spatial", ("Mean (box), Gaussian and median filters", "Laplacian and Sobel X/Y")),
        ("E Histogram", ("Histogram of the current image in each panel", "Histogram equalization")),
        ("F Morphology", ("Global or Otsu threshold", "Erode, dilate, open, close")),
    )
    creativity = (
        ("Live preview, undo/redo, clickable history",
         "Linked zoom/pan, pixel inspector, Space compare",
         "Before/After wipe (Ctrl+B)",
         "Drag & drop, recent files, eight sample images",
         "Histogram dock and window (B/G/R)",
         "Use Result as Original, dark theme"),
        ("FFT spectrum and frequency filters",
         "Frequency Inspector (Ctrl+F)",
         "CLAHE, unsharp mask, Canny",
         "Noise generator, sepia, bilateral filter",
         "Keyboard shortcuts, Unicode paths",
         "Automated tests (pytest)"),
    )
    cells = [checklist_cell(title, items) for title, items in groups]
    rows = [f"<tr>{left}{right}</tr>" for left, right in zip(cells[::2], cells[1::2])]
    rows.append('<tr><td colspan="2" bgcolor="#dce8f6"><b>Creativity</b></td></tr>')
    rows.append("<tr>" + "".join(checklist_cell("", column) for column in creativity) + "</tr>")
    return '<table width="100%" cellspacing="2" cellpadding="4">' + "".join(rows) + "</table>"


def param_value(value):
    if isinstance(value, bool):
        return "On" if value else "Off"
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def param_range(param):
    if param.kind == "choice":
        return " / ".join(param.choices)
    if param.kind == "bool":
        return "Off / On"
    suffix = " (odd)" if param.kind == "int" and param.step == 2 and param.min % 2 else ""
    return f"{param_value(param.min)} to {param_value(param.max)}{suffix}"


def parameter_table():
    selections = (
        (("rotate90",), (("k", "Clockwise quarter-turns"),)),
        (("rotate",), (("angle_deg", "Angle (°)"), ("expand", "Expand canvas"), ("border", "Fill"))),
        (("scale",), (("sx", "X factor"), ("sy", "Y factor"), ("interp", "Interpolation"))),
        (("translate",), (("dx", "dx (px)"), ("dy", "dy (px)"))),
        (("shear",), (("shx", "X shear"), ("shy", "Y shear"), ("expand", "Expand canvas"))),
        (("contrast_stretch",), (("low_pct", "Lower percentile"), ("high_pct", "Upper percentile"))),
        (("gamma",), (("g", "Exponent"),)),
        (("box", "laplacian"), (("k", "Kernel width"),)),
        (("gaussian",), (("k", "Kernel width"), ("sigma", "Sigma"))),
        (("median",), (("k", "Kernel width"),)),
        (("sobel",), (("direction", "Derivative"), ("k", "Kernel width"))),
        (("threshold",), (("method", "Method"), ("t", "Global cutoff"), ("invert", "Invert"))),
        (("erode", "dilate", "opening", "closing"),
         (("k", "Kernel width"), ("shape", "Shape"), ("iterations", "Iterations"))),
        (("clahe",), (("clip", "Clip limit"), ("tile", "Tiles per axis"))),
        (("unsharp",), (("k", "Blur kernel"), ("amount", "Amount"))),
        (("canny",), (("t1", "Lower threshold"), ("t2", "Upper threshold"))),
    )
    operations = {op.id: op for op in OPERATIONS}
    rows = ['<tr bgcolor="#dce8f6"><td width="25%"><b>Operation</b></td>'
            '<td width="60%"><b>Parameter and range</b></td>'
            '<td width="15%"><b>Default</b></td></tr>']
    for ids, columns in selections:
        grouped = {}
        for op_id in ids:
            op = operations[op_id]
            params = {param.name: param for param in op.params}
            selected = tuple(params[name] for name, _ in columns)
            grouped.setdefault(selected, []).append(op.label)
        for params, names in grouped.items():
            labels = escape(", ".join(names))
            ranges = "<br>".join(escape(f"{label} · {param_range(param)}")
                                 for param, (_, label) in zip(params, columns))
            defaults = "<br>".join(escape(param_value(param.default)) for param in params)
            color = "#f2f6fb" if len(rows) % 2 else "#ffffff"
            rows.append(f'<tr bgcolor="{color}"><td><b>{labels}</b></td>'
                        f"<td>{ranges}</td><td>{defaults}</td></tr>")
    return '<table width="100%" cellspacing="0" cellpadding="4">' + "".join(rows) + "</table>"


def readme_pages(width, height):
    header = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body { font-family: 'Segoe UI'; font-size: 9.5pt; color: #18283c; }
h1 { font-size: 25pt; color: #14355c; margin: 0 0 4px 0; }
h2 { font-size: 13pt; color: #14355c; margin: 12px 0 3px 0; }
p { margin: 0 0 6px 0; }
td { vertical-align: top; }
.check { color: #11613e; font-family: 'Segoe UI Symbol'; }
</style></head><body>
"""
    overview = f"""<h1>DIP Midterm</h1>
<p><b>Oguz Cetin</b> · COMP 4360 Digital Image Processing · {date.today():%d %B %Y}</p>
<h2>1. Overview &amp; UI map</h2>
<p>DIP Midterm is a PySide6 and OpenCV desktop app for applying and comparing image-processing
operations. Open a file, drop it onto the window, or choose File → Sample Images. Adjust an
operation in the left dock, click Apply to keep it, then use File → Save Result As to export.</p>
<p><img src="ui_map.png" width="{width}" height="{height}"></p>
<table width="100%" cellspacing="2" cellpadding="3" bgcolor="#f2f6fb">
<tr><td width="34%"><b>1 Operations panel</b><br>Pick a group and apply an operation.</td>
<td width="33%"><b>2 Original</b><br>View the current source image.</td>
<td width="33%"><b>3 Result</b><br>View the current edit or preview.</td></tr>
<tr><td><b>4 Histogram dock</b><br>Track the distribution in both panels.</td>
<td><b>5 History dock</b><br>Click a saved step to revisit it.</td>
<td><b>6 Status bar / pixel inspector</b><br>Hover an image for coordinates and values.</td></tr>
</table>
<h2>2. Implemented features</h2>
{feature_checklist()}
"""
    reference = f"""<h2 style="margin-top: 0">3. Key parameters</h2>
{parameter_table()}
<p style="margin-top: 5px">Match X and Y factors for uniform scale. Positive rotation is counterclockwise.
Gaussian sigma 0 derives the blur from its kernel width. Gamma above 1 darkens the image.</p>
<h2>4. Shortcuts</h2>
<p>Ctrl+O Open · Ctrl+S Save · Ctrl+Z Undo · Ctrl+Y Redo · Ctrl+R Reset · Ctrl+0 Fit · Ctrl+1 100%
· Space Compare · Ctrl+B Wipe · Ctrl+F Frequency Inspector</p>
<h2>5. Known limitations</h2>
<p>Processing is 8-bit. Loading normalizes 16-bit images to 8-bit and discards alpha. Laplacian,
Sobel, Canny, threshold and FFT spectrum produce grayscale output. History keeps up to 30 snapshots in RAM,
including the original. Large images slow live previews. The Windows-only single-file executable
can take a few seconds to start while it unpacks.</p>
"""
    return (f"{header}{body}</body></html>" for body in (overview, reference))


def write_pdf(path, image):
    writer = QPdfWriter(str(path))
    writer.setTitle("DIP Midterm")
    writer.setCreator("DIP Midterm README generator")
    writer.setResolution(96)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(11, 11, 11, 11), QPageLayout.Unit.Millimeter)
    area = writer.pageLayout().paintRectPixels(writer.resolution())

    width = area.width() - 1
    height = round(width * image.height() / image.width())
    page_rect = QRectF(0, 0, area.width(), area.height())
    with QPainter(writer) as painter:
        if not painter.isActive():
            raise RuntimeError(f"Could not write {path}")
        for page, html in enumerate(readme_pages(width, height)):
            document = QTextDocument()
            document.setDocumentMargin(0)
            document.setPageSize(page_rect.size())
            document.documentLayout().setPaintDevice(writer)
            document.addResource(QTextDocument.ResourceType.ImageResource, QUrl("ui_map.png"), image)
            document.setHtml(html)
            if document.pageCount() != 1:
                raise RuntimeError(f"README content overflows page {page + 1} of 2")
            if page and not writer.newPage():
                raise RuntimeError(f"Could not add a page to {path}")
            document.drawContents(painter, page_rect)


def verify_pdf(path):
    pdf = QPdfDocument()
    try:
        if pdf.load(str(path)) != QPdfDocument.Error.None_:
            raise RuntimeError(f"Could not reopen the generated PDF: {pdf.error().name}")
        pages = pdf.pageCount()
        if not 1 <= pages <= 2:
            raise RuntimeError(f"Expected a one- or two-page README, got {pages} pages")
        return pages
    finally:
        pdf.close()


def main():
    app = QApplication([])
    if sys.platform == "win32" and app.platformName() == "offscreen":
        # The Windows offscreen plugin may start with an empty font database.
        fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        for name in ("segoeui.ttf", "segoeuib.ttf", "seguisym.ttf"):
            if QFontDatabase.addApplicationFont(str(fonts / name)) == -1:
                raise RuntimeError(f"Could not load the offscreen font {name}")
        app.setFont(QFont("Segoe UI", 9))
    configure_appearance(app)
    image = capture_ui(app)
    output = ROOT / "README.pdf"
    with TemporaryDirectory(dir=ROOT, prefix=".readme-") as folder:
        candidate = Path(folder) / output.name
        write_pdf(candidate, image)
        pages = verify_pdf(candidate)
        candidate.replace(output)
    print(f"{output} ({pages} pages)")


if __name__ == "__main__":
    main()
