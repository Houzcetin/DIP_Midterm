import cv2
import numpy as np
import pytest

from ops.frequency import KINDS, SHAPES, filter_mask, frequency_filter, spectrum


@pytest.mark.parametrize("size", [(47, 63), (48, 64)])
@pytest.mark.parametrize("log", [True, False])
def test_spectrum_has_centered_dc_and_grayscale_output(size, log):
    rng = np.random.default_rng(4360)
    img = rng.integers(115, 140, (*size, 3), dtype=np.uint8)
    result = spectrum(img, log=log)
    assert result.shape == size
    assert result.dtype == np.uint8
    assert np.unravel_index(result.argmax(), size) == tuple(n // 2 for n in size)
    assert result.max() == 255


@pytest.mark.parametrize("shape", SHAPES)
def test_lowpass_reduces_laplacian_variance(shape):
    img = np.random.default_rng(4360).integers(0, 256, (64, 64), dtype=np.uint8)
    result = frequency_filter(img, "lowpass", shape, cutoff=6)
    before = cv2.Laplacian(img, cv2.CV_64F).var()
    after = cv2.Laplacian(result, cv2.CV_64F).var()
    assert after < 0.1 * before


@pytest.mark.parametrize("shape", SHAPES)
def test_dc_gain_and_constant_image(shape):
    size = (47, 64)
    center = tuple(n // 2 for n in size)
    assert filter_mask(size, "highpass", shape)[center] == 0
    assert filter_mask(size, "lowpass", shape)[center] == 1
    img = np.full(size, 130, dtype=np.uint8)
    assert not frequency_filter(img, "highpass", shape).any()
    np.testing.assert_array_equal(frequency_filter(img, "lowpass", shape), img)


@pytest.mark.parametrize("size", [(31, 49), (32, 48)])
def test_gaussian_mask_is_symmetric_about_dc(size):
    mask = filter_mask(size, "lowpass", "gaussian", cutoff=7)
    # For even lengths the negative Nyquist bin is its own periodic mirror.
    y, x = ((2 * (n // 2) - np.arange(n)) % n for n in size)
    np.testing.assert_array_equal(mask, mask[np.ix_(y, x)])
    assert np.all((mask >= 0) & (mask <= 1))


@pytest.mark.parametrize("shape", SHAPES)
def test_band_masks_are_complementary(shape):
    args = (shape, 12, 6, 3)
    bandpass = filter_mask((31, 49), "bandpass", *args)
    bandstop = filter_mask((31, 49), "bandstop", *args)
    np.testing.assert_allclose(bandpass + bandstop, 1)
    assert bandpass[15, 24 + 12] == 1
    assert bandstop[15, 24 + 12] == 0


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("size", [(31, 47), (32, 48)])
def test_filter_preserves_independent_bgr_channels(kind, size):
    img = np.random.default_rng(4360).integers(0, 256, (*size, 3), dtype=np.uint8)
    result = frequency_filter(img, kind, "butterworth", cutoff=8)
    assert result.shape == img.shape
    assert result.dtype == np.uint8
    for channel in range(3):
        np.testing.assert_array_equal(
            result[..., channel], frequency_filter(img[..., channel], kind, "butterworth", cutoff=8),
        )
