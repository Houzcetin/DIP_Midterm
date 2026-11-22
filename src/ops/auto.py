"""Measure an image and plan deterministic, classical enhancements."""

from collections.abc import Callable
from dataclasses import dataclass
from math import log
from typing import NamedTuple

import cv2
import numpy as np

from ._validation import image
from .registry import get_op

# Impulses must be at a luminance endpoint and at least 64 levels from the median.
IMPULSE_DISTANCE = 64
IMPULSE_THRESHOLD = 0.01
SEVERE_IMPULSE_THRESHOLD = 0.08
GAUSSIAN_THRESHOLD = 4.0  # Standard deviation in 8-bit luminance levels.
CAST_THRESHOLD = 0.06  # Maximum gray-world channel mean deviation, on 0..1.

# Tone thresholds are fractions of the full luminance scale.
DARK_THRESHOLD = 0.32
BRIGHT_THRESHOLD = 0.68
TARGET_BRIGHTNESS = 0.47
LOW_DYNAMIC_RANGE = 0.28
FINAL_STRETCH_RANGE = 0.6  # Re-stretch after gamma/CLAHE when the result still spans less than this.
LOW_EXPOSED_DYNAMIC_RANGE = 0.14  # Give gamma priority for compressed shadows/highlights.
MIN_STRETCH_RANGE = 8 / 255  # Avoid pulling an almost flat image across the full scale.
LOW_LOCAL_CONTRAST = 0.04
BINARY_FRACTION = 0.9  # Share of near-black/near-white pixels that marks a two-level image.

# Spatial detail is measured at up to 512 pixels along the longest side.
DETAIL_SIZE = 512
LOCAL_WINDOW = 15
LOW_SHARPNESS = 0.0006  # Variance of the 4-neighbor Laplacian on 0..1 luminance.

_NOISE_KERNEL = np.outer([1, -2, 1], [1, -2, 1]).astype(np.float32)


@dataclass(frozen=True, slots=True)
class ImageStats:
    mean_brightness: float
    contrast: float
    dynamic_range: float
    local_contrast: float
    salt_pepper_fraction: float
    gaussian_sigma: float
    sharpness: float
    color_cast: float
    is_grayscale: bool
    saturation_mean: float


class Step(NamedTuple):
    op_id: str
    params: dict[str, int | float]
    reason_key: str
    reason_args: dict[str, float]


@dataclass(frozen=True, slots=True)
class AppliedStep:
    step: Step
    output: np.ndarray


@dataclass(frozen=True, slots=True)
class AutoResult:
    before: ImageStats
    steps: list[AppliedStep]
    after: ImageStats


def analyze(img: np.ndarray) -> ImageStats:
    """Measure gray or BGR uint8 without changing the input."""
    image(img)
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    median = cv2.medianBlur(gray, 3)
    impulses = ((gray == 0) | (gray == 255)) & (cv2.absdiff(gray, median) >= IMPULSE_DISTANCE)
    low, high = np.percentile(gray, (2, 98))

    height, width = gray.shape
    sigma = 0.0
    if min(height, width) >= 3:
        residual = cv2.filter2D(gray, cv2.CV_32F, _NOISE_KERNEL)[1:-1, 1:-1]
        # MAD resists edges. A Gaussian's MAD is 0.67449 sigma and the kernel L2 norm is 6.
        sigma = float(np.median(np.abs(residual - np.median(residual))) / (0.67449 * 6))

    detail = gray
    if max(height, width) > DETAIL_SIZE:
        scale = DETAIL_SIZE / max(height, width)
        detail = cv2.resize(gray, (max(1, round(width * scale)), max(1, round(height * scale))),
                            interpolation=cv2.INTER_AREA)
    detail = detail.astype(np.float32) / 255
    sharpness = float(cv2.Laplacian(detail, cv2.CV_32F).var(dtype=np.float64))
    local_mean = cv2.blur(detail, (LOCAL_WINDOW, LOCAL_WINDOW))
    local_variance = cv2.blur(detail ** 2, (LOCAL_WINDOW, LOCAL_WINDOW)) - local_mean ** 2
    local_contrast = float(np.sqrt(np.maximum(local_variance, 0).mean()))

    is_grayscale = img.ndim == 2 or (
        np.array_equal(img[:, :, 0], img[:, :, 1]) and np.array_equal(img[:, :, 1], img[:, :, 2]))
    cast = saturation = 0.0
    if not is_grayscale:
        means = img.mean(axis=(0, 1)) / 255
        cast = float(np.max(np.abs(means - means.mean())))
        saturation = float(cv2.cvtColor(img, cv2.COLOR_BGR2HSV)[:, :, 1].mean() / 255)

    return ImageStats(float(gray.mean() / 255), float(gray.std() / 255), float((high - low) / 255),
                      local_contrast, float(impulses.mean()), sigma, sharpness, cast,
                      is_grayscale, saturation)


def _is_binary(img: np.ndarray) -> bool:
    """True when nearly every pixel is pure black or pure white."""
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return float(((gray <= 8) | (gray >= 247)).mean()) >= BINARY_FRACTION


def _plan_and_apply(img: np.ndarray, before: ImageStats) -> AutoResult:
    working, stats = img, before
    applied: list[AppliedStep] = []

    def try_step(op_id: str, params: dict[str, int | float], reason_key: str,
                 improves: Callable[[ImageStats], bool], **reason_args: float) -> None:
        nonlocal working, stats
        output = get_op(op_id).func(working, **params)
        measured = analyze(output)
        if improves(measured):
            applied.append(AppliedStep(Step(op_id, params, reason_key, reason_args), output))
            working, stats = output, measured

    if stats.salt_pepper_fraction >= IMPULSE_THRESHOLD:
        k = 5 if stats.salt_pepper_fraction >= SEVERE_IMPULSE_THRESHOLD else 3
        try_step("median", {"k": k}, "Reduce isolated black and white pixels ({fraction:.1%}).",
                 lambda after: after.salt_pepper_fraction < stats.salt_pepper_fraction,
                 fraction=stats.salt_pepper_fraction)
    elif stats.gaussian_sigma >= GAUSSIAN_THRESHOLD:
        sigma = stats.gaussian_sigma
        radius = min(4, max(2, round(sigma / 4)))
        try_step("bilateral", {"d": 2 * radius + 1, "sigma_color": min(255, round(4 * sigma)),
                               "sigma_space": radius},
                 "Reduce estimated Gaussian noise (sigma {sigma:.1f}) while preserving edges.",
                 lambda after: after.gaussian_sigma < stats.gaussian_sigma, sigma=sigma)

    if not stats.is_grayscale and stats.color_cast >= CAST_THRESHOLD:
        try_step("white_balance", {"strength": 1.0},
                 "Reduce the imbalance between channel means ({cast:.2f}).",
                 lambda after: after.color_cast < stats.color_cast, cast=stats.color_cast)

    if _is_binary(working):
        # Tone curves and sharpening cannot add information to a black-and-white image.
        return AutoResult(before, applied, stats)

    off_target = not DARK_THRESHOLD <= stats.mean_brightness <= BRIGHT_THRESHOLD
    range_limit = LOW_EXPOSED_DYNAMIC_RANGE if off_target else LOW_DYNAMIC_RANGE
    if MIN_STRETCH_RANGE <= stats.dynamic_range < range_limit:
        try_step("contrast_stretch", {"low_pct": 2.0, "high_pct": 98.0},
                 "Expand the narrow luminance range ({spread:.2f}).",
                 lambda after: after.dynamic_range > stats.dynamic_range, spread=stats.dynamic_range)
    if stats.local_contrast < LOW_LOCAL_CONTRAST and stats.dynamic_range >= MIN_STRETCH_RANGE:
        tile = min(8, max(1, min(working.shape[:2]) // 16))
        try_step("clahe", {"clip": 2.0, "tile": tile},
                 "Increase weak local contrast ({contrast:.3f}).",
                 lambda after: after.local_contrast > stats.local_contrast,
                 contrast=stats.local_contrast)

    mean = stats.mean_brightness
    if 0 < mean < 1 and not DARK_THRESHOLD <= mean <= BRIGHT_THRESHOLD:
        spec = get_op("gamma").params[0]
        exponent = log(TARGET_BRIGHTNESS) / log(mean)
        exponent = min(spec.max, max(spec.min, exponent))
        exponent = round(spec.min + round((exponent - spec.min) / spec.step) * spec.step, 2)
        try_step("gamma", {"g": exponent}, "Move mean brightness ({mean:.2f}) toward {target:.2f}.",
                 lambda after: (abs(after.mean_brightness - TARGET_BRIGHTNESS)
                                < abs(mean - TARGET_BRIGHTNESS)
                                and (stats.dynamic_range < LOW_DYNAMIC_RANGE
                                     or after.dynamic_range >= LOW_DYNAMIC_RANGE)),
                 mean=mean, target=TARGET_BRIGHTNESS)

    if (any(entry.step.op_id in ("gamma", "clahe") for entry in applied)
            and MIN_STRETCH_RANGE <= stats.dynamic_range < FINAL_STRETCH_RANGE):
        # Tone corrections can leave a washed-out result; spread it once more if that stays in range.
        try_step("contrast_stretch", {"low_pct": 1.0, "high_pct": 99.0},
                 "Expand the narrow luminance range ({spread:.2f}).",
                 lambda after: (after.dynamic_range > stats.dynamic_range
                                and DARK_THRESHOLD <= after.mean_brightness <= BRIGHT_THRESHOLD),
                 spread=stats.dynamic_range)

    if (0 < stats.sharpness < LOW_SHARPNESS and stats.gaussian_sigma < GAUSSIAN_THRESHOLD
            and stats.salt_pepper_fraction < IMPULSE_THRESHOLD):
        try_step("unsharp", {"k": 5, "amount": 1.0},
                 "Bring out soft edges (sharpness {sharpness:.5f}).",
                 lambda after: (after.sharpness > stats.sharpness
                                and after.gaussian_sigma < GAUSSIAN_THRESHOLD),
                 sharpness=stats.sharpness)

    return AutoResult(before, applied, stats)


def plan(stats: ImageStats, img: np.ndarray) -> list[Step]:
    """Return the ordered steps for the supplied image and its initial measurements."""
    return [entry.step for entry in _plan_and_apply(img, stats).steps]


def run(img: np.ndarray) -> AutoResult:
    """Return the measurements and output of each accepted registry operation."""
    return _plan_and_apply(img, analyze(img))
