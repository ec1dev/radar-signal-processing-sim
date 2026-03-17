"""Tests for MTI (Moving Target Indication) mode."""

import numpy as np
import pytest

from radar_sim.models import RadarParams, RawReturn
from radar_sim.modes.mti import MTIMode


@pytest.fixture
def mti() -> MTIMode:
    return MTIMode(RadarParams(), num_pulses=2)


@pytest.fixture
def mti3() -> MTIMode:
    return MTIMode(RadarParams(), num_pulses=3)


class TestMTIFilterResponse:
    def test_zero_at_dc(self, mti: MTIMode) -> None:
        """Clutter at f=0 should be completely cancelled."""
        np.testing.assert_allclose(mti.mti_filter_response(0.0), 0.0, atol=1e-15)

    def test_zero_at_blind_speed(self, mti: MTIMode) -> None:
        """Response should be zero at f = n * PRF (blind speeds)."""
        prf = mti.radar.prf
        for n in range(1, 4):
            doppler_at_blind = n * prf
            np.testing.assert_allclose(
                mti.mti_filter_response(doppler_at_blind), 0.0, atol=1e-10
            )

    def test_max_at_half_prf(self, mti: MTIMode) -> None:
        """Response should be maximum (1.0) at f = PRF/2."""
        response = mti.mti_filter_response(mti.radar.prf / 2)
        np.testing.assert_allclose(response, 1.0, atol=1e-10)

    def test_intermediate_value(self, mti: MTIMode) -> None:
        """Response at PRF/4 should be sin^2(pi/4) = 0.5."""
        response = mti.mti_filter_response(mti.radar.prf / 4)
        np.testing.assert_allclose(response, 0.5, atol=1e-10)

    def test_three_pulse_deeper_null(self, mti: MTIMode, mti3: MTIMode) -> None:
        """3-pulse canceller should have steeper roll-off near DC."""
        small_doppler = 10.0  # Hz, near clutter
        gain_2 = mti.mti_filter_response(small_doppler)
        gain_3 = mti3.mti_filter_response(small_doppler)
        assert gain_3 < gain_2  # 3-pulse suppresses more near DC

    def test_three_pulse_also_maxes_at_half_prf(self, mti3: MTIMode) -> None:
        response = mti3.mti_filter_response(mti3.radar.prf / 2)
        np.testing.assert_allclose(response, 1.0, atol=1e-10)


class TestMTIDetection:
    def test_blind_speed_target_not_detected(self, mti: MTIMode) -> None:
        """Target at exactly the first blind speed should vanish."""
        radar = mti.radar
        blind_v = radar.wavelength * radar.prf / 2  # 30 m/s
        blind_doppler = 2 * blind_v / radar.wavelength  # = PRF
        strong_power = radar.noise_power * 1000
        returns = [RawReturn(
            range_m=20000, radial_velocity=blind_v,
            received_power=strong_power, doppler_hz=blind_doppler,
            target_id="blind_tgt",
        )]
        dets = mti.process(returns)
        target_dets = [d for d in dets if d.target_id == "blind_tgt"]
        assert len(target_dets) == 0

    def test_clutter_suppressed(self, mti: MTIMode) -> None:
        """Near-zero Doppler clutter should be cancelled."""
        strong_clutter = mti.radar.noise_power * 10000
        returns = [RawReturn(
            range_m=5000, radial_velocity=0.0,
            received_power=strong_clutter, doppler_hz=0.0,
            is_clutter=True,
        )]
        dets = mti.process(returns)
        clutter_dets = [d for d in dets if d.is_clutter]
        assert len(clutter_dets) == 0

    def test_moving_target_detected(self, mti: MTIMode) -> None:
        """Target with good Doppler should be detected."""
        radar = mti.radar
        v = 100.0  # m/s
        doppler = 2 * v / radar.wavelength
        strong_power = radar.noise_power * 1000
        returns = [RawReturn(
            range_m=20000, radial_velocity=v,
            received_power=strong_power, doppler_hz=doppler,
            target_id="moving",
        )]
        dets = mti.process(returns)
        target_dets = [d for d in dets if d.target_id == "moving"]
        assert len(target_dets) >= 1

    def test_name_contains_pulse_count(self, mti: MTIMode) -> None:
        assert "2" in mti.name
