"""Tests for core data models: RadarParams, Target, Detection, RawReturn."""

import numpy as np
import pytest

from radar_sim.models import (
    C, K_BOLTZ, Target, RadarParams, RadarPosition, ClutterParams,
    Detection, RadarMode, RawReturn,
)


class TestRadarParams:
    """Verify computed properties against hand-calculated values."""

    def test_wavelength(self) -> None:
        r = RadarParams()
        np.testing.assert_allclose(r.wavelength, C / 10.0e9, rtol=1e-10)
        assert abs(r.wavelength - 0.029979) < 1e-4

    def test_gain_linear(self) -> None:
        r = RadarParams()
        np.testing.assert_allclose(r.gain_linear, 10 ** (33.0 / 10), rtol=1e-10)

    def test_noise_figure_linear(self) -> None:
        r = RadarParams()
        np.testing.assert_allclose(r.noise_figure_linear, 10 ** (4.0 / 10), rtol=1e-10)

    def test_noise_power(self) -> None:
        r = RadarParams()
        expected = K_BOLTZ * 290.0 * 1.0e6 * r.noise_figure_linear
        np.testing.assert_allclose(r.noise_power, expected, rtol=1e-10)

    def test_max_unambiguous_range(self) -> None:
        r = RadarParams()
        expected = C / (2 * 2000.0)
        np.testing.assert_allclose(r.max_unambiguous_range, expected, rtol=1e-10)
        assert abs(r.max_unambiguous_range - 74948.0) < 1.0

    def test_range_resolution(self) -> None:
        r = RadarParams()
        expected = C * 1.0e-6 / 2
        np.testing.assert_allclose(r.range_resolution, expected, rtol=1e-10)
        assert abs(r.range_resolution - 150.0) < 0.2

    def test_max_unambiguous_velocity(self) -> None:
        r = RadarParams()
        expected = r.wavelength * r.prf / 4
        np.testing.assert_allclose(r.max_unambiguous_velocity, expected, rtol=1e-10)

    def test_blind_speeds(self) -> None:
        r = RadarParams()
        bs = r.blind_speeds
        assert len(bs) == 5
        first = r.wavelength * r.prf / 2
        np.testing.assert_allclose(bs[0], first, rtol=1e-10)
        assert abs(bs[0] - 30.0) < 0.1

    def test_custom_frequency(self) -> None:
        r = RadarParams(frequency=3.0e9)
        np.testing.assert_allclose(r.wavelength, C / 3.0e9, rtol=1e-10)


class TestTarget:
    def test_update_position(self) -> None:
        t = Target(id="t1", x=0, y=0, altitude=1000, vx=100, vy=-200, rcs=1.0)
        t.update(2.0)
        assert t.x == 200.0
        assert t.y == -400.0

    def test_speed(self) -> None:
        t = Target(id="t1", x=0, y=0, altitude=0, vx=3, vy=4, rcs=1.0)
        np.testing.assert_allclose(t.speed, 5.0)

    def test_heading(self) -> None:
        t = Target(id="t1", x=0, y=0, altitude=0, vx=0, vy=100, rcs=1.0)
        np.testing.assert_allclose(t.heading_rad, 0.0, atol=1e-10)

    def test_zero_velocity(self) -> None:
        t = Target(id="t1", x=10, y=20, altitude=0, vx=0, vy=0, rcs=1.0)
        t.update(100.0)
        assert t.x == 10
        assert t.y == 20
        np.testing.assert_allclose(t.speed, 0.0)


class TestDetection:
    def test_defaults(self) -> None:
        d = Detection(range_m=1000.0)
        assert d.velocity_mps is None
        assert d.snr_db == 0.0
        assert d.target_id is None
        assert d.is_clutter is False
        assert d.is_ambiguous is False

    def test_full_creation(self) -> None:
        d = Detection(
            range_m=5000, velocity_mps=100.0, snr_db=20.0,
            target_id="tgt_1", is_clutter=False, is_ambiguous=True,
        )
        assert d.range_m == 5000
        assert d.is_ambiguous is True


class TestRawReturn:
    def test_creation(self) -> None:
        r = RawReturn(
            range_m=10000, radial_velocity=50,
            received_power=1e-12, doppler_hz=3333,
            target_id="t1",
        )
        assert r.range_m == 10000
        assert r.is_clutter is False

    def test_clutter_return(self) -> None:
        r = RawReturn(
            range_m=5000, radial_velocity=0.1,
            received_power=1e-10, doppler_hz=6.7,
            is_clutter=True,
        )
        assert r.target_id is None
        assert r.is_clutter is True


class TestClutterParams:
    def test_reflectivity_linear(self) -> None:
        c = ClutterParams(reflectivity_db=-20.0)
        np.testing.assert_allclose(c.reflectivity_linear, 0.01, rtol=1e-10)

    def test_disabled(self) -> None:
        c = ClutterParams(enabled=False)
        assert c.enabled is False


class TestRadarMode:
    def test_enum_values(self) -> None:
        assert RadarMode.SRC.value == "src"
        assert RadarMode.PULSE_DOPPLER.value == "pulse_doppler"
