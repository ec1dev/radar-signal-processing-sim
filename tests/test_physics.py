"""Tests for the physics engine: radar equation, Doppler, clutter, SNR."""

import numpy as np
import pytest

from radar_sim.models import (
    C, Target, RadarParams, RadarPosition, ClutterParams, RawReturn,
)
from radar_sim.radar.physics import PhysicsEngine


@pytest.fixture
def default_engine() -> PhysicsEngine:
    return PhysicsEngine(RadarParams(), RadarPosition(), ClutterParams())


@pytest.fixture
def no_clutter_engine() -> PhysicsEngine:
    return PhysicsEngine(RadarParams(), RadarPosition(), ClutterParams(enabled=False))


class TestRadarEquation:
    def test_received_power_known_target(self, no_clutter_engine: PhysicsEngine) -> None:
        """Hand-calculate Pr for a target directly north at 40 km."""
        radar = no_clutter_engine.radar
        tgt = Target(id="t", x=0, y=40000, altitude=5000, vx=0, vy=-250, rcs=3.0)
        ret = no_clutter_engine.compute_target_return(tgt)
        assert ret is not None

        # Hand calculation
        r = 40000.0  # target at same altitude as radar, directly north
        numerator = radar.power * radar.gain_linear**2 * radar.wavelength**2 * tgt.rcs
        denominator = (4 * np.pi)**3 * r**4
        expected_pr = numerator / denominator

        np.testing.assert_allclose(ret.received_power, expected_pr, rtol=0.01)

    def test_inverse_r4_scaling(self, no_clutter_engine: PhysicsEngine) -> None:
        """Power should scale as R^-4."""
        tgt_near = Target(id="t1", x=0, y=10000, altitude=5000, vx=0, vy=0, rcs=1.0)
        tgt_far = Target(id="t2", x=0, y=20000, altitude=5000, vx=0, vy=0, rcs=1.0)
        ret_near = no_clutter_engine.compute_target_return(tgt_near)
        ret_far = no_clutter_engine.compute_target_return(tgt_far)
        assert ret_near is not None and ret_far is not None
        ratio = ret_near.received_power / ret_far.received_power
        np.testing.assert_allclose(ratio, 16.0, rtol=0.01)

    def test_returns_none_for_zero_range(self, no_clutter_engine: PhysicsEngine) -> None:
        tgt = Target(id="t", x=0, y=0, altitude=5000, vx=0, vy=0, rcs=1.0)
        ret = no_clutter_engine.compute_target_return(tgt)
        assert ret is None


class TestDoppler:
    def test_closing_target_positive_doppler(self, no_clutter_engine: PhysicsEngine) -> None:
        """Target heading toward radar should have positive Doppler."""
        tgt = Target(id="t", x=0, y=20000, altitude=5000, vx=0, vy=-250, rcs=1.0)
        ret = no_clutter_engine.compute_target_return(tgt)
        assert ret is not None
        assert ret.doppler_hz > 0
        assert ret.radial_velocity > 0

    def test_doppler_value(self, no_clutter_engine: PhysicsEngine) -> None:
        """250 m/s at X-band: f_d = 2*250/0.03 ~ 16667 Hz."""
        tgt = Target(id="t", x=0, y=20000, altitude=5000, vx=0, vy=-250, rcs=1.0)
        ret = no_clutter_engine.compute_target_return(tgt)
        assert ret is not None
        expected_fd = 2 * ret.radial_velocity / no_clutter_engine.radar.wavelength
        np.testing.assert_allclose(ret.doppler_hz, expected_fd, rtol=1e-6)

    def test_crossing_target_low_doppler(self, no_clutter_engine: PhysicsEngine) -> None:
        """Target moving perpendicular should have near-zero radial velocity."""
        tgt = Target(id="t", x=0, y=20000, altitude=5000, vx=200, vy=0, rcs=1.0)
        ret = no_clutter_engine.compute_target_return(tgt)
        assert ret is not None
        assert abs(ret.radial_velocity) < 1.0


class TestClutter:
    def test_clutter_count(self, default_engine: PhysicsEngine) -> None:
        returns = default_engine.compute_clutter_returns()
        assert len(returns) == 200

    def test_clutter_near_zero_velocity(self, default_engine: PhysicsEngine) -> None:
        np.random.seed(42)
        returns = default_engine.compute_clutter_returns()
        for ret in returns:
            assert ret.is_clutter is True
            assert ret.target_id is None
            assert abs(ret.radial_velocity) < 5.0  # should be near zero

    def test_disabled_clutter(self) -> None:
        engine = PhysicsEngine(RadarParams(), RadarPosition(), ClutterParams(enabled=False))
        assert engine.compute_clutter_returns() == []

    def test_compute_all_returns_includes_both(self, default_engine: PhysicsEngine) -> None:
        targets = [Target(id="t1", x=0, y=20000, altitude=5000, vx=0, vy=-100, rcs=5.0)]
        returns = default_engine.compute_all_returns(targets)
        target_returns = [r for r in returns if not r.is_clutter]
        clutter_returns = [r for r in returns if r.is_clutter]
        assert len(target_returns) == 1
        assert len(clutter_returns) == 200


class TestSNR:
    def test_snr_computation(self, no_clutter_engine: PhysicsEngine) -> None:
        tgt = Target(id="t", x=0, y=20000, altitude=5000, vx=0, vy=-100, rcs=5.0)
        ret = no_clutter_engine.compute_target_return(tgt)
        assert ret is not None
        snr_db = no_clutter_engine.compute_snr(ret)
        expected = 10 * np.log10(ret.received_power / no_clutter_engine.radar.noise_power)
        np.testing.assert_allclose(snr_db, expected, rtol=1e-10)

    def test_snr_zero_power(self, no_clutter_engine: PhysicsEngine) -> None:
        ret = RawReturn(range_m=1000, radial_velocity=0, received_power=0, doppler_hz=0)
        assert no_clutter_engine.compute_snr(ret) == -np.inf
