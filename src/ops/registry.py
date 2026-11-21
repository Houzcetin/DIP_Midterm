"""Declarative metadata for building operation controls; no UI dependencies.

Invoke an entry with op.func(img, **{p.name: p.default for p in op.params}).
compute_hist is an analysis helper, so it is not an image-producing operation here.
"""

from dataclasses import dataclass, field
from typing import Callable, Literal

import numpy as np

from . import affine, basics, extras, filters, histogram, intensity, morphology

Group = Literal["A Basics", "B Affine", "C Intensity", "D Spatial Filters",
                "E Histogram", "F Morphology", "Extras"]
Kind = Literal["int", "float", "choice", "bool"]


@dataclass(frozen=True, slots=True)
class ParamSpec:
    name: str
    label: str
    kind: Kind
    default: int | float | str | bool
    min: int | float | None = None
    max: int | float | None = None
    step: int | float | None = None
    choices: tuple[str, ...] = ()
    tooltip: str = ""


@dataclass(frozen=True, slots=True)
class OperationSpec:
    id: str
    group: Group
    label: str
    func: Callable[..., np.ndarray]
    params: list[ParamSpec] = field(default_factory=list)
    live: bool = False


_KERNEL = ParamSpec("k", "Kernel size", "int", 3, 1, 31, 2,
                    tooltip="Odd neighborhood width; even sizes round up.")
_SHAPE = ParamSpec("shape", "Kernel shape", "choice", "rect",
                   choices=("rect", "ellipse", "cross"), tooltip="Structuring element shape.")
_ITERATIONS = ParamSpec("iterations", "Iterations", "int", 1, 1, 10, 1,
                        tooltip="Number of erosions/dilations in each stage.")
_EXPAND = ParamSpec("expand", "Expand canvas", "bool", True,
                    tooltip="Fit the full transformed image without cropping.")


OPERATIONS: list[OperationSpec] = [
    OperationSpec("to_grayscale", "A Basics", "Grayscale", basics.to_grayscale, live=True),
    OperationSpec("flip", "A Basics", "Flip", basics.flip, [
        ParamSpec("mode", "Direction", "choice", "h", choices=("h", "v", "both"),
                  tooltip="Horizontal, vertical, or both axes.")], live=True),
    OperationSpec("rotate90", "A Basics", "Rotate 90 degrees", basics.rotate90, [
        ParamSpec("k", "Quarter-turns clockwise", "int", 1, -3, 3, 1,
                  tooltip="Modulo 4: 1 is clockwise; -1 or 3 is counterclockwise.")], live=True),

    OperationSpec("rotate", "B Affine", "Rotate", affine.rotate, [
        ParamSpec("angle_deg", "Angle (degrees)", "float", 30.0, -180.0, 180.0, 1.0,
                  tooltip="Positive angles turn counterclockwise about the center."),
        _EXPAND,
        ParamSpec("border", "Border intensity", "int", 0, 0, 255, 1,
                  tooltip="Fill intensity outside the image; 0 is black.")], live=True),
    OperationSpec("scale", "B Affine", "Scale", affine.scale, [
        ParamSpec("sx", "Horizontal factor", "float", 1.0, 0.1, 4.0, 0.1,
                  tooltip="Width multiplier; result is at least one pixel."),
        ParamSpec("sy", "Vertical factor", "float", 1.0, 0.1, 4.0, 0.1,
                  tooltip="Height multiplier; result is at least one pixel."),
        ParamSpec("interp", "Interpolation", "choice", "linear",
                  choices=("nearest", "linear", "cubic", "area", "lanczos"),
                  tooltip="How resized pixel values are sampled.")], live=True),
    OperationSpec("translate", "B Affine", "Translate", affine.translate, [
        ParamSpec("dx", "Horizontal shift (pixels)", "int", 10, -500, 500, 1,
                  tooltip="Positive shifts right; canvas size stays fixed."),
        ParamSpec("dy", "Vertical shift (pixels)", "int", 10, -500, 500, 1,
                  tooltip="Positive shifts down; exposed pixels are black.")], live=True),
    OperationSpec("shear", "B Affine", "Shear", affine.shear, [
        ParamSpec("shx", "Horizontal shear", "float", 0.2, -0.9, 0.9, 0.05,
                  tooltip="Adds shx times y to x; use 0 for no horizontal shear."),
        ParamSpec("shy", "Vertical shear", "float", 0.0, -0.9, 0.9, 0.05,
                  tooltip="Adds shy times x to y; use 0 for no vertical shear."),
        _EXPAND], live=True),

    OperationSpec("contrast_stretch", "C Intensity", "Contrast stretch", intensity.contrast_stretch, [
        ParamSpec("low_pct", "Lower percentile", "float", 2.0, 0.0, 49.0, 1.0,
                  tooltip="Per-channel percentile mapped to black."),
        ParamSpec("high_pct", "Upper percentile", "float", 98.0, 51.0, 100.0, 1.0,
                  tooltip="Per-channel percentile mapped to white.")], live=True),
    OperationSpec("gamma", "C Intensity", "Gamma correction", intensity.gamma, [
        ParamSpec("g", "Gamma", "float", 1.0, 0.1, 5.0, 0.1,
                  tooltip="Exponent: above 1 darkens; below 1 brightens; 1 is unchanged.")], live=True),
    OperationSpec("negative", "C Intensity", "Negative", intensity.negative, live=True),

    OperationSpec("box", "D Spatial Filters", "Box blur", filters.box, [_KERNEL], live=True),
    OperationSpec("gaussian", "D Spatial Filters", "Gaussian blur", filters.gaussian, [
        _KERNEL,
        ParamSpec("sigma", "Sigma", "float", 0.0, 0.0, 20.0, 0.1,
                  tooltip="Gaussian standard deviation; 0 derives it from kernel size.")], live=True),
    OperationSpec("median", "D Spatial Filters", "Median filter", filters.median, [
        ParamSpec("k", "Kernel size", "int", 3, 3, 31, 2,
                  tooltip="Odd neighborhood width, at least 3.")], live=True),
    OperationSpec("laplacian", "D Spatial Filters", "Laplacian edges", filters.laplacian,
                  [_KERNEL], live=True),
    OperationSpec("sobel", "D Spatial Filters", "Sobel edges", filters.sobel, [
        ParamSpec("direction", "Direction", "choice", "both", choices=("x", "y", "both"),
                  tooltip="Absolute x/y derivative or Euclidean magnitude; output is gray."),
        _KERNEL], live=True),

    OperationSpec("equalize", "E Histogram", "Histogram equalization", histogram.equalize, live=True),

    OperationSpec("threshold", "F Morphology", "Threshold", morphology.threshold, [
        ParamSpec("method", "Method", "choice", "global", choices=("global", "otsu"),
                  tooltip="Global uses t; Otsu estimates the threshold automatically."),
        ParamSpec("t", "Threshold", "int", 127, 0, 255, 1,
                  tooltip="Global cutoff; output is binary gray."),
        ParamSpec("invert", "Invert", "bool", False,
                  tooltip="Swap black and white in the binary result.")], live=True),
    OperationSpec("erode", "F Morphology", "Erode", morphology.erode,
                  [_KERNEL, _SHAPE, _ITERATIONS], live=True),
    OperationSpec("dilate", "F Morphology", "Dilate", morphology.dilate,
                  [_KERNEL, _SHAPE, _ITERATIONS], live=True),
    OperationSpec("opening", "F Morphology", "Opening", morphology.opening,
                  [_KERNEL, _SHAPE, _ITERATIONS], live=True),
    OperationSpec("closing", "F Morphology", "Closing", morphology.closing,
                  [_KERNEL, _SHAPE, _ITERATIONS], live=True),

    OperationSpec("clahe", "Extras", "CLAHE", extras.clahe, [
        ParamSpec("clip", "Clip limit", "float", 2.0, 0.1, 10.0, 0.1,
                  tooltip="Contrast limit; color equalizes LAB lightness only."),
        ParamSpec("tile", "Tiles per axis", "int", 8, 1, 32, 1,
                  tooltip="Number of grid tiles per axis, not tile width in pixels.")], live=True),
    OperationSpec("unsharp", "Extras", "Unsharp mask", extras.unsharp, [
        ParamSpec("k", "Blur kernel size", "int", 5, 1, 31, 2,
                  tooltip="Odd Gaussian width used to extract detail."),
        ParamSpec("amount", "Sharpening amount", "float", 1.0, 0.0, 5.0, 0.1,
                  tooltip="Multiplier of the detail residual; 0 is unchanged.")], live=True),
    OperationSpec("canny", "Extras", "Canny edges", extras.canny, [
        ParamSpec("t1", "Lower threshold", "int", 100, 0, 255, 1,
                  tooltip="Weak-edge threshold; the pair is sorted automatically."),
        ParamSpec("t2", "Upper threshold", "int", 200, 0, 255, 1,
                  tooltip="Strong-edge threshold; output is gray.")], live=True),
    OperationSpec("add_noise", "Extras", "Add noise", extras.add_noise, [
        ParamSpec("kind", "Noise type", "choice", "salt_pepper",
                  choices=("salt_pepper", "gaussian"), tooltip="Impulse noise or additive normal noise."),
        ParamSpec("amount", "Amount", "float", 0.05, 0.0, 1.0, 0.01,
                  tooltip="Salt/pepper pixel fraction, or Gaussian standard deviation divided by 255."),
        ParamSpec("seed", "Random seed", "int", 0, 0, 2147483647, 1,
                  tooltip="Same seed gives repeatable noise; the Python API also accepts None.")]),
    OperationSpec("sepia", "Extras", "Sepia", extras.sepia, live=True),
    OperationSpec("bilateral", "Extras", "Bilateral filter", extras.bilateral, [
        ParamSpec("d", "Diameter", "int", 9, 1, 31, 2,
                  tooltip="Odd neighborhood diameter."),
        ParamSpec("sigma_color", "Color sigma", "float", 75.0, 0.0, 255.0, 1.0,
                  tooltip="Larger values mix more dissimilar intensities."),
        ParamSpec("sigma_space", "Spatial sigma", "float", 75.0, 0.0, 255.0, 1.0,
                  tooltip="Larger values mix pixels over larger distances.")]),
]


def get_op(id: str) -> OperationSpec:
    """Return an operation by its stable id; raise KeyError for an unknown id."""
    for op in OPERATIONS:
        if op.id == id:
            return op
    raise KeyError(id)
