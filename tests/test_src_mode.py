"""Tests for SRC (Search) mode."""

import numpy as np
import pytest

from radar_sim.models import RadarParams, RawReturn, Detection
from radar_sim.modes.src import SRCMode


@pytest.fixture
def src_mode() -> SRCMode:
    return SRCMode(RadarParams())


def _make_target_return(range_m: float, power: float, target_id: str = "t1") -> RawReturn:
    return RawReturn(
        range_m=range_m, radial_velocity=100, received_power=power,
        doppler_hz=6667, target_id=target_id,
    )


def _make_clutter_return(range_m: float, power: float) -> RawReturn:
    return RawReturn(
        range_m=range_m, radial_velocity=0.1, received_power=power,
        doppler_hz=6.7, is_clutter=True,
    )


class TestSRCDetection:
    def test_detects_strong_target(self, src_mode: SRCMode) -> None:
        """A strong target well above noise should be detected."""
        strong_power = src_mode.radar.noise_power * 1000
        returns = [_make_target_return(20000, strong_power)]
        dets = src_mode.process(returns)
        target_dets = [d for d in dets if d.target_id is not None]
        assert len(target_dets) >= 1

    def test_misses_weak_target(self, src_mode: SRCMode) -> None:
        """A target below threshold should not be detected."""
        weak_power = src_mode.radar.noise_power * 0.1
        returns = [_make_target_return(20000, weak_power)]
        dets = src_mode.process(returns)
        target_dets = [d for d in dets if d.target_id is not None]
        assert len(target_dets) == 0

    def test_no_velocity_measurement(self, src_mode: SRCMode) -> None:
        """SRC should never provide velocity."""
        strong_power = src_mode.radar.noise_power * 1000
        returns = [_make_target_return(20000, strong_power)]
        dets = src_mode.process(returns)
        for d in dets:
            assert d.velocity_mps is None

    def test_does_not_reject_clutter(self, src_mode: SRCMode) -> None:
        """SRC should detect strong clutter as detections."""
        strong_clutter = src_mode.radar.noise_power * 1000
        returns = [_make_clutter_return(5000, strong_clutter)]
        dets = src_mode.process(returns)
        clutter_dets = [d for d in dets if d.is_clutter]
        assert len(clutter_dets) >= 1

    def test_lower_threshold_more_detections(self) -> None:
        """Lowering threshold should detect more returns."""
        radar_high = RadarParams(detection_threshold_db=15.0)
        radar_low = RadarParams(detection_threshold_db=8.0)
        moderate_power = RadarParams().noise_power * 20  # ~13 dB SNR
        returns = [_make_target_return(20000, moderate_power)]
        dets_high = SRCMode(radar_high).process(returns)
        dets_low = SRCMode(radar_low).process(returns)
        assert len(dets_low) >= len(dets_high)

    def test_name_and_description(self, src_mode: SRCMode) -> None:
        assert "SRC" in src_mode.name
        assert len(src_mode.description) > 0
