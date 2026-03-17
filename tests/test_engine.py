"""Tests for the simulation engine."""

import numpy as np
import pytest

from radar_sim.models import RadarParams, RadarMode
from radar_sim.engine import SimulationEngine


@pytest.fixture
def engine() -> SimulationEngine:
    return SimulationEngine()


class TestEngineInit:
    def test_default_init(self, engine: SimulationEngine) -> None:
        assert engine.scenario is not None
        assert engine.radar is not None
        assert len(engine.scenario.targets) == 5

    def test_starts_in_src_mode(self, engine: SimulationEngine) -> None:
        assert engine._active_mode == RadarMode.SRC


class TestModeSwitching:
    def test_switch_to_mti(self, engine: SimulationEngine) -> None:
        engine.set_mode(RadarMode.MTI)
        assert engine._active_mode == RadarMode.MTI

    def test_switch_to_pd(self, engine: SimulationEngine) -> None:
        engine.set_mode(RadarMode.PULSE_DOPPLER)
        assert engine._active_mode == RadarMode.PULSE_DOPPLER

    def test_switch_to_tws(self, engine: SimulationEngine) -> None:
        engine.set_mode(RadarMode.TWS)
        assert engine._active_mode == RadarMode.TWS


class TestTick:
    def test_advances_time(self, engine: SimulationEngine) -> None:
        frame = engine.tick(dt=1.0)
        assert frame.time == 1.0
        frame2 = engine.tick(dt=0.5)
        np.testing.assert_allclose(frame2.time, 1.5)

    def test_zero_dt(self, engine: SimulationEngine) -> None:
        frame = engine.tick(dt=0.0)
        assert frame.time == 0.0
        assert len(frame.detections) > 0

    def test_frame_has_ground_truth(self, engine: SimulationEngine) -> None:
        frame = engine.tick(dt=0.0)
        assert len(frame.targets) == 5
        assert all("id" in t for t in frame.targets)
        assert all("range_m" in t for t in frame.targets)

    def test_frame_has_params_summary(self, engine: SimulationEngine) -> None:
        frame = engine.tick(dt=0.0)
        assert "frequency_ghz" in frame.radar_params_summary
        assert "prf_hz" in frame.radar_params_summary

    def test_all_modes_produce_detections(self, engine: SimulationEngine) -> None:
        """Every registered mode should return a list of Detection objects."""
        np.random.seed(42)
        for mode in [RadarMode.SRC, RadarMode.MTI, RadarMode.PULSE_DOPPLER]:
            engine.set_mode(mode)
            frame = engine.tick(dt=0.0)
            assert isinstance(frame.detections, list)
            assert frame.mode == engine.active_mode.name


class TestParameterUpdate:
    def test_update_prf(self, engine: SimulationEngine) -> None:
        engine.update_radar_param("prf", 5000.0)
        assert engine.radar.prf == 5000.0

    def test_invalid_param_raises(self, engine: SimulationEngine) -> None:
        with pytest.raises(ValueError):
            engine.update_radar_param("nonexistent", 42)
