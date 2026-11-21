"""Public operation contracts, registry integration, and known-value regression tests."""

import inspect

import cv2
import numpy as np
import pytest

from ops import affine, basics, extras, filters, histogram, intensity, morphology
from ops.registry import OPERATIONS, get_op


@pytest.fixture(params=[(64, 48), (64, 48, 3)], ids=["gray", "bgr"])
def img(request):
    return np.random.default_rng(4360).integers(0, 256, request.param, dtype=np.uint8)


def _assert_result(op, source):
    before = source.copy()
    result = op.func(source, **{p.name: p.default for p in op.params})
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.uint8
    assert result.ndim in (2, 3)
    assert result.shape[0] > 0 and result.shape[1] > 0
    if result.ndim == 3:
        assert result.shape[2] == 3
    assert not np.shares_memory(result, source)
    np.testing.assert_array_equal(source, before)
    expected_channels = 1 if source.ndim == 2 else 3
    if op.id in {"to_grayscale", "laplacian", "sobel", "threshold", "canny", "spectrum"}:
        expected_channels = 1
    elif op.id == "sepia":
        expected_channels = 3
    assert result.ndim == (2 if expected_channels == 1 else 3)
    if op.id == "rotate90":
        assert result.shape[:2] == source.shape[:2][::-1]
    elif op.id in {"rotate", "shear"}:
        assert np.prod(result.shape[:2]) >= np.prod(source.shape[:2])
    else:
        assert result.shape[:2] == source.shape[:2]


@pytest.mark.parametrize("op", OPERATIONS, ids=lambda op: op.id)
def test_registry_defaults(op, img):
    _assert_result(op, img)


@pytest.mark.parametrize("op", OPERATIONS, ids=lambda op: op.id)
def test_noncontiguous_readonly_inputs(op, img):
    view = img[::-1, ::2]
    view.flags.writeable = False
    _assert_result(op, view)


@pytest.mark.parametrize("op", OPERATIONS, ids=lambda op: op.id)
@pytest.mark.parametrize("shape", [(1, 1), (1, 1, 3)], ids=["gray", "bgr"])
def test_tiny_inputs(op, shape):
    _assert_result(op, np.full(shape, 127, dtype=np.uint8))


def test_registry_schema():
    expected = {"to_grayscale", "flip", "rotate90", "rotate", "scale", "translate", "shear",
                "contrast_stretch", "gamma", "negative", "box", "gaussian", "median",
                "laplacian", "sobel", "equalize", "threshold", "erode", "dilate", "opening",
                "closing", "clahe", "unsharp", "canny", "add_noise", "sepia", "bilateral",
                "spectrum", "frequency_filter"}
    assert {op.id for op in OPERATIONS} == expected
    assert len(OPERATIONS) == len(expected)
    groups = {"A Basics", "B Affine", "C Intensity", "D Spatial Filters",
              "E Histogram", "F Morphology", "Extras", "G Frequency"}
    for op in OPERATIONS:
        assert get_op(op.id) is op
        assert op.group in groups
        assert op.label and op.func.__doc__ and isinstance(op.live, bool)
        assert isinstance(op.params, list)
        signature = inspect.signature(op.func)
        assert set(signature.parameters) - {"img"} == {p.name for p in op.params}
        assert len({p.name for p in op.params}) == len(op.params)
        signature.bind(object(), **{p.name: p.default for p in op.params})
        for p in op.params:
            assert p.label and p.tooltip
            assert p.kind in {"int", "float", "choice", "bool"}
            if p.kind == "choice":
                assert p.default in p.choices
            elif p.kind == "bool":
                assert isinstance(p.default, bool)
            else:
                assert p.min <= p.default <= p.max and p.step > 0
                if p.kind == "int":
                    assert isinstance(p.default, int)
    with pytest.raises(KeyError):
        get_op("does_not_exist")


def test_negative_involution(img):
    np.testing.assert_array_equal(intensity.negative(intensity.negative(img)), img)


def test_gamma_identity(img):
    np.testing.assert_array_equal(intensity.gamma(img, 1.0), img)


def test_flip_twice(img):
    np.testing.assert_array_equal(basics.flip(basics.flip(img, "h"), "h"), img)


def test_rotate90_four_times(img):
    result = img
    for _ in range(4):
        result = basics.rotate90(result, 1)
    np.testing.assert_array_equal(result, img)


@pytest.mark.parametrize("k", [-5, -1, 0, 1, 2, 3, 4, 9])
def test_rotate90_direction_and_modulo(img, k):
    np.testing.assert_array_equal(basics.rotate90(img, k), np.rot90(img, -k))


@pytest.mark.parametrize("angle", [90, -90, 270, 450])
def test_rotate_expanded_right_angle(img, angle):
    result = affine.rotate(img, angle, expand=True)
    assert result.shape[:2] == img.shape[:2][::-1]
    np.testing.assert_array_equal(result, np.rot90(img, int(angle / 90)))


def test_translate_single_pixel():
    img = np.zeros((9, 11), dtype=np.uint8)
    img[3, 4] = 255
    expected = np.zeros_like(img)
    expected[5, 7] = 255
    np.testing.assert_array_equal(affine.translate(img, 3, 2), expected)
    assert affine.translate(img, -100, 0).sum() == 0


@pytest.mark.parametrize("shx,shy", [(0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5), (0.3, -0.2)])
def test_shear_expansion(img, shx, shy):
    h, w = img.shape[:2]
    result = affine.shear(img, shx, shy)
    assert result.shape[:2] == (int(np.ceil(h + abs(shy) * w)),
                                int(np.ceil(w + abs(shx) * h)))
    assert affine.shear(img, shx, shy, expand=False).shape == img.shape


def test_affine_identity_and_border(img):
    for result in (affine.rotate(img, 0), affine.shear(img, 0, 0),
                   affine.translate(img, 0, 0), affine.scale(img, 1, 1)):
        np.testing.assert_array_equal(result, img)
        assert not np.shares_memory(result, img)
    assert affine.rotate(img, 45, expand=False).shape == img.shape
    filled = affine.rotate(np.full_like(img, 255), 45, border=17)
    assert np.all(filled[0, 0] == 17)


@pytest.mark.parametrize("interp", ["nearest", "linear", "cubic", "area", "lanczos", cv2.INTER_LINEAR])
def test_scale_dimensions(img, interp):
    assert affine.scale(img, 2, 0.5, interp).shape[:2] == (32, 96)
    assert affine.scale(img, 0.0001, 0.0001, interp).shape[:2] == (1, 1)


@pytest.mark.parametrize("method", ["global", "otsu"])
def test_threshold_binary_and_invert(img, method):
    result = morphology.threshold(img, method)
    assert result.ndim == 2
    assert set(np.unique(result)) <= {0, 255}
    np.testing.assert_array_equal(morphology.threshold(img, method, invert=True), 255 - result)


def test_equalize_increases_range():
    img = np.tile(np.arange(100, 111, dtype=np.uint8), (20, 1))
    assert np.ptp(histogram.equalize(img)) > np.ptp(img)
    bgr = np.repeat(img[..., None], 3, axis=2)
    assert np.ptp(histogram.equalize(bgr)) > np.ptp(bgr)


def test_compute_hist_counts(img):
    before = img.copy()
    hist = histogram.compute_hist(img)
    assert list(hist) == (["gray"] if img.ndim == 2 else ["b", "g", "r"])
    for index, counts in enumerate(hist.values()):
        channel = img if img.ndim == 2 else img[:, :, index]
        assert counts.shape == (256,) and np.issubdtype(counts.dtype, np.floating)
        assert counts.sum() == img.shape[0] * img.shape[1]
        np.testing.assert_array_equal(counts, np.bincount(channel.ravel(), minlength=256))
    np.testing.assert_array_equal(img, before)


def test_contrast_stretch_per_channel_and_constant():
    img = np.array([[[10, 100, 7], [20, 200, 7]]], dtype=np.uint8)
    expected = np.array([[[0, 0, 7], [255, 255, 7]]], dtype=np.uint8)
    np.testing.assert_array_equal(intensity.contrast_stretch(img, 0, 100), expected)
    gray = np.full((4, 5), 42, dtype=np.uint8)
    np.testing.assert_array_equal(intensity.contrast_stretch(gray), gray)


def test_grayscale_and_flip_known_values():
    img = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
    np.testing.assert_array_equal(basics.to_grayscale(img), img)
    np.testing.assert_array_equal(basics.flip(img, "h"), img[:, ::-1])
    np.testing.assert_array_equal(basics.flip(img, "v"), img[::-1])
    np.testing.assert_array_equal(basics.flip(img, "both"), img[::-1, ::-1])
    red = np.array([[[0, 0, 255]]], dtype=np.uint8)
    assert basics.to_grayscale(red).item() == 76


@pytest.mark.parametrize("func", [filters.box, filters.gaussian, filters.median, filters.laplacian,
                                  morphology.erode, morphology.dilate, morphology.opening,
                                  morphology.closing, extras.unsharp])
def test_kernel_clamping(img, func):
    np.testing.assert_array_equal(func(img, 4), func(img, 5))
    assert func(img, -4).dtype == np.uint8


@pytest.mark.parametrize("direction", ["x", "y", "both"])
def test_sobel_response(direction):
    img = np.tile(np.arange(9, dtype=np.uint8), (7, 1))
    result = filters.sobel(img, direction, 3)
    if direction == "y":
        assert not result.any()
    else:
        assert np.all(result[1:-1, 1:-1] == 8)


@pytest.mark.parametrize("shape", ["rect", "ellipse", "cross"])
def test_morphology_shapes(shape):
    point = np.zeros((9, 9), dtype=np.uint8)
    point[4, 4] = 255
    grown = morphology.dilate(point, shape=shape)
    assert np.count_nonzero(grown) == (9 if shape == "rect" else 5)
    assert not morphology.opening(point, shape=shape).any()
    hole = 255 - point
    assert np.all(morphology.closing(hole, shape=shape) == 255)


@pytest.mark.parametrize("kind", ["salt_pepper", "gaussian"])
def test_noise_repeatability_and_zero(img, kind):
    state = np.random.get_state()
    result = extras.add_noise(img, kind, 0.2, seed=123)
    np.testing.assert_array_equal(result, extras.add_noise(img, kind, 0.2, seed=123))
    np.testing.assert_array_equal(extras.add_noise(img, kind, 0, seed=123), img)
    after = np.random.get_state()
    for before_part, after_part in zip(state, after):
        np.testing.assert_array_equal(before_part, after_part)
    assert not np.array_equal(result, img)


def test_salt_pepper_uses_whole_pixels():
    img = np.full((30, 40, 3), 127, dtype=np.uint8)
    result = extras.add_noise(img, "salt_pepper", 1, seed=4)
    assert set(np.unique(result)) == {0, 255}
    assert np.all(result[:, :, 0] == result[:, :, 1])
    assert np.all(result[:, :, 1] == result[:, :, 2])


def test_extras_known_values(img):
    np.testing.assert_array_equal(extras.unsharp(img, amount=0), img)
    np.testing.assert_array_equal(extras.canny(img, 200, 100), extras.canny(img, 100, 200))
    white = np.array([[[255, 255, 255]]], dtype=np.uint8)
    np.testing.assert_array_equal(extras.sepia(white), [[[239, 255, 255]]])


@pytest.mark.parametrize("op", OPERATIONS, ids=lambda op: op.id)
@pytest.mark.parametrize("bad", [np.zeros((2, 2), dtype=np.float32),
                                 np.zeros((2, 2, 4), dtype=np.uint8),
                                 np.empty((0, 2), dtype=np.uint8)])
def test_invalid_images(op, bad):
    with pytest.raises((TypeError, ValueError)):
        op.func(bad, **{p.name: p.default for p in op.params})


@pytest.mark.parametrize("func,kwargs", [
    (basics.flip, {"mode": "bad"}),
    (affine.scale, {"sx": 0, "sy": 1}),
    (affine.scale, {"sx": 1, "sy": 1, "interp": "bad"}),
    (affine.rotate, {"angle_deg": float("nan")}),
    (affine.shear, {"shx": 1, "shy": 1}),
    (intensity.gamma, {"g": 0}),
    (intensity.gamma, {"g": float("inf")}),
    (intensity.contrast_stretch, {"low_pct": 99, "high_pct": 1}),
    (filters.sobel, {"direction": "bad"}),
    (morphology.threshold, {"method": "bad"}),
    (morphology.erode, {"shape": "bad"}),
    (extras.add_noise, {"kind": "bad", "amount": 0.1}),
])
def test_invalid_parameters(func, kwargs):
    with pytest.raises(ValueError):
        func(np.zeros((5, 6), dtype=np.uint8), **kwargs)
