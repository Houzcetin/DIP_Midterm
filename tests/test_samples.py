import numpy as np
import pytest

from core.samples import SAMPLES
from ops.frequency import frequency_filter, spectrum


@pytest.mark.parametrize("name", SAMPLES)
def test_sample_generation_is_deterministic(name):
    _, _, generate = SAMPLES[name]
    sample = generate()
    expected_hw = (800, 600) if name == "document" else (480, 640)
    assert sample.shape == (*expected_hw, 3)
    assert sample.dtype == np.uint8
    np.testing.assert_array_equal(sample, generate())


def test_periodic_sample_has_peaks_at_the_suggested_band_stop_radius():
    sample = SAMPLES["periodic_noise"][2]()
    before = spectrum(sample)
    filtered = frequency_filter(sample, "bandstop", "ideal", cutoff=31, width=4)
    after = spectrum(filtered)
    cy, cx = np.array(before.shape) // 2
    for peak in ((cy + 8, cx + 30), (cy - 8, cx - 30)):
        assert before[peak] > np.percentile(before, 99)
        assert after[peak] < before[peak]
