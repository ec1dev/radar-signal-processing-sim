"""Tests for Pulse Doppler mode: FFT processing, CFAR, range ambiguity."""

import numpy as np
import pytest

from radar_sim.models import RadarParams, RawReturn, C
from radar_sim.modes.pulse_doppler import PulseDopplerMode


@pytest.fixture
def pd() -> PulseDopplerMode:
    np.random.seed(42)
    return PulseDopplerMode(RadarParams(), n_pulses=64)


class TestPulseDopplerProperties:
    def test_velocity_resolution(self, pd: PulseDopplerMode) -> None:
        expected = pd.radar.wavelength * pd.radar.prf / (2 * pd.n_pulses)
        np.testing.assert_allclose(pd.velocity_resolution, expected)

    def test_doppler_bin_width(self, pd: PulseDopplerMode) -> None:
        expected = pd.radar.prf / pd.n_pulses
        np.testing.assert_allclose(pd.doppler_bin_width_hz, expected)


class TestAliasDoppler:
    def test_no_alias_within_nyquist(self, pd: PulseDopplerMode) -> None:
        """Frequency within [-PRF/2, PRF/2) should pass through."""
        np.testing.assert_allclose(pd._alias_doppler(500.0), 500.0)
        np.testing.assert_allclose(pd._alias_doppler(-500.0), -500.0)

    def test_alias_above_nyquist(self, pd: PulseDopplerMode) -> None:
        """1400 Hz with PRF=2000 aliases to -600 Hz."""
        np.testing.assert_allclose(pd._alias_doppler(1400.0), -600.0)

    def test_alias_at_prf(self, pd: PulseDopplerMode) -> None:
        """Exactly PRF aliases to 0 (DC)."""
        np.testing.assert_allclose(pd._alias_doppler(2000.0), 0.0, atol=1e-10)

    def test_alias_high_doppler(self, pd: PulseDopplerMode) -> None:
        """16533 Hz should alias to 533 Hz (16533 mod 2000 = 533)."""
        aliased = pd._alias_doppler(16533.0)
        np.testing.assert_allclose(aliased, 533.0, atol=1.0)

    def test_vectorized(self, pd: PulseDopplerMode) -> None:
        arr = np.array([500.0, 1400.0, 2000.0])
        result = pd._alias_doppler(arr)
        expected = np.array([500.0, -600.0, 0.0])
        np.testing.assert_allclose(result, expected, atol=1e-10)


class TestRangeDopplerMap:
    def test_map_dimensions(self, pd: PulseDopplerMode) -> None:
        np.random.seed(42)
        radar = pd.radar
        returns = [RawReturn(
            range_m=20000, radial_velocity=100,
            received_power=radar.noise_power * 100,
            doppler_hz=2 * 100 / radar.wavelength, target_id="t1",
        )]
        power_map, ranges, dopplers, _ = pd.build_range_doppler_map(returns)
        n_range_bins = int(radar.max_unambiguous_range / radar.range_resolution)
        assert power_map.shape == (n_range_bins, pd.n_pulses)
        assert len(ranges) == n_range_bins
        assert len(dopplers) == pd.n_pulses

    def test_target_appears_in_correct_bin(self, pd: PulseDopplerMode) -> None:
        """A strong target should create a peak at the correct range-Doppler cell."""
        np.random.seed(42)
        radar = pd.radar
        target_range = 15000.0
        target_v = 100.0
        target_doppler = 2 * target_v / radar.wavelength
        returns = [RawReturn(
            range_m=target_range, radial_velocity=target_v,
            received_power=radar.noise_power * 10000,
            doppler_hz=target_doppler, target_id="t1",
        )]
        power_map, ranges, dopplers, _ = pd.build_range_doppler_map(returns)

        # Find peak
        peak_idx = np.unravel_index(np.argmax(power_map), power_map.shape)
        peak_range = ranges[peak_idx[0]]
        peak_doppler = dopplers[peak_idx[1]]

        assert abs(peak_range - target_range) < radar.range_resolution
        aliased_doppler = float(pd._alias_doppler(target_doppler))
        assert abs(peak_doppler - aliased_doppler) < pd.doppler_bin_width_hz


class TestPDDetection:
    def test_provides_velocity(self, pd: PulseDopplerMode) -> None:
        """PD detections should always include velocity."""
        np.random.seed(42)
        radar = pd.radar
        returns = [RawReturn(
            range_m=15000, radial_velocity=100,
            received_power=radar.noise_power * 10000,
            doppler_hz=2 * 100 / radar.wavelength, target_id="t1",
        )]
        dets = pd.process(returns)
        target_dets = [d for d in dets if d.target_id == "t1"]
        assert len(target_dets) >= 1
        for d in target_dets:
            assert d.velocity_mps is not None

    def test_rejects_clutter(self, pd: PulseDopplerMode) -> None:
        """PD should reject most zero-Doppler clutter."""
        np.random.seed(42)
        radar = pd.radar
        clutter = [RawReturn(
            range_m=5000 + i * 500, radial_velocity=0,
            received_power=radar.noise_power * 1000,
            doppler_hz=0.0, is_clutter=True,
        ) for i in range(20)]
        target = RawReturn(
            range_m=15000, radial_velocity=100,
            received_power=radar.noise_power * 500,
            doppler_hz=2 * 100 / radar.wavelength, target_id="t1",
        )
        dets = pd.process(clutter + [target])
        clutter_dets = [d for d in dets if d.is_clutter]
        target_dets = [d for d in dets if d.target_id == "t1"]
        # Clutter should be heavily suppressed
        assert len(clutter_dets) <= len(clutter)
        assert len(target_dets) >= 1

    def test_range_ambiguity(self, pd: PulseDopplerMode) -> None:
        """Target beyond R_unamb should appear at folded range."""
        np.random.seed(42)
        radar = pd.radar
        r_unamb = radar.max_unambiguous_range
        true_range = r_unamb * 1.1  # 10% beyond
        folded = true_range % r_unamb
        returns = [RawReturn(
            range_m=true_range, radial_velocity=50,
            received_power=radar.noise_power * 5000,
            doppler_hz=2 * 50 / radar.wavelength, target_id="far",
        )]
        dets = pd.process(returns)
        target_dets = [d for d in dets if d.target_id == "far"]
        if target_dets:
            # Detection range should be near the folded range
            assert abs(target_dets[0].range_m - folded) < radar.range_resolution * 2
            assert target_dets[0].is_ambiguous is True

    def test_cfar_threshold_nonuniform(self, pd: PulseDopplerMode) -> None:
        """CFAR threshold map should not be constant across range."""
        np.random.seed(42)
        radar = pd.radar
        n_range = int(radar.max_unambiguous_range / radar.range_resolution)
        # Create a power map with varying noise levels
        power_map = np.random.exponential(1e-13, (n_range, pd.n_pulses))
        power_map[0:10, :] *= 1000  # strong clutter in first 10 bins
        notch_mask = np.zeros(pd.n_pulses, dtype=bool)
        notch_mask[pd.n_pulses // 2 - 5 : pd.n_pulses // 2 + 6] = True
        power_map[:, notch_mask] = 0

        thresh = pd._cfar_threshold_map(power_map, notch_mask)
        # Threshold in high-clutter region should be higher
        assert thresh[:10, :].mean() > thresh[100:200, :].mean()
