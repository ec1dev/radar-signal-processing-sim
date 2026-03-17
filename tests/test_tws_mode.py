"""Tests for TWS mode: EKF, scan controller, association, track manager, integration."""

import numpy as np
import pytest

from radar_sim.models import RadarParams, RadarPosition, Detection, RawReturn
from radar_sim.modes.tws.ekf_tracker import EKFTracker
from radar_sim.modes.tws.scan_controller import ScanController
from radar_sim.modes.tws.track_manager import TrackManager, TrackStatus
from radar_sim.modes.tws.association import Associator
from radar_sim.modes.tws.tws_mode import TWSMode


# ── EKF tests ────────────────────────────────────────────────────────


class TestEKFTracker:
    @pytest.fixture
    def ekf(self) -> EKFTracker:
        state = np.array([1000.0, 0.0, 2000.0, 0.0])
        P = np.diag([100.0, 10.0, 100.0, 10.0])
        R = np.diag([150.0**2, np.radians(3.0)**2])
        return EKFTracker(state, P, process_noise_q=100.0, R_meas=R)

    def test_predict_zero_velocity_no_position_change(self, ekf: EKFTracker) -> None:
        x_before = ekf.position
        ekf.predict(1.0)
        np.testing.assert_allclose(ekf.position, x_before, atol=1e-10)

    def test_predict_advances_position(self) -> None:
        state = np.array([0.0, 100.0, 0.0, 200.0])  # vx=100, vy=200
        P = np.diag([100.0, 10.0, 100.0, 10.0])
        R = np.diag([150.0**2, np.radians(3.0)**2])
        ekf = EKFTracker(state, P, 100.0, R)
        ekf.predict(2.0)
        np.testing.assert_allclose(ekf.position[0], 200.0, atol=1e-6)
        np.testing.assert_allclose(ekf.position[1], 400.0, atol=1e-6)

    def test_covariance_grows_on_predict(self, ekf: EKFTracker) -> None:
        trace_before = np.trace(ekf.P)
        ekf.predict(1.0)
        assert np.trace(ekf.P) > trace_before

    def test_covariance_shrinks_on_update(self, ekf: EKFTracker) -> None:
        ekf.predict(1.0)
        trace_after_predict = np.trace(ekf.P)
        r = np.sqrt(1000**2 + 2000**2)
        az = np.arctan2(1000, 2000)
        ekf.update(r, az)
        assert np.trace(ekf.P) < trace_after_predict

    def test_covariance_stays_symmetric(self, ekf: EKFTracker) -> None:
        ekf.predict(0.5)
        r, az = ekf.predicted_measurement()
        ekf.update(r + 10, az + 0.01)
        np.testing.assert_allclose(ekf.P, ekf.P.T, atol=1e-12)

    def test_covariance_positive_semidefinite(self, ekf: EKFTracker) -> None:
        ekf.predict(1.0)
        r, az = ekf.predicted_measurement()
        ekf.update(r, az)
        eigvals = np.linalg.eigvalsh(ekf.P)
        assert np.all(eigvals >= -1e-10)

    def test_angle_wrapping(self) -> None:
        """Target near the +/-pi boundary should handle wrapping."""
        # Place target at azimuth near pi (almost due south-west)
        state = np.array([-100.0, 0.0, -10000.0, 0.0])
        P = np.diag([1000.0, 100.0, 1000.0, 100.0])
        R = np.diag([150.0**2, np.radians(3.0)**2])
        ekf = EKFTracker(state, P, 100.0, R)
        ekf.predict(0.1)
        # Measurement on the other side of the pi/-pi boundary
        r = np.sqrt(100**2 + 10000**2)
        az = np.arctan2(-100, -10000)  # near -pi
        ekf.update(r, az + 0.01)  # tiny perturbation
        # Should not diverge
        assert ekf.position_uncertainty < 10000

    def test_position_uncertainty_property(self, ekf: EKFTracker) -> None:
        unc = ekf.position_uncertainty
        expected = np.sqrt(ekf.P[0, 0] + ekf.P[2, 2])
        np.testing.assert_allclose(unc, expected)


# ── Scan controller tests ────────────────────────────────────────────


class TestScanController:
    @pytest.fixture
    def scan(self) -> ScanController:
        return ScanController(
            scan_volume_deg=120.0, scan_rate_deg_per_s=60.0,
            beamwidth_az_deg=3.0,
        )

    def test_beam_advances(self, scan: ScanController) -> None:
        az0 = scan.current_beam_az
        scan.update(0.5)
        az1 = scan.current_beam_az
        np.testing.assert_allclose(az1 - az0, 30.0, atol=0.1)

    def test_beam_reverses_at_limit(self, scan: ScanController) -> None:
        # Sweep to the right limit
        scan.update(2.0)  # 120 deg at 60 deg/s = 2s to reach right limit
        assert scan.completed_scans >= 1
        # Next update should move left
        az_at_limit = scan.current_beam_az
        scan.update(0.1)
        assert scan.current_beam_az < az_at_limit

    def test_is_illuminated_within_beam(self, scan: ScanController) -> None:
        assert scan.is_illuminated(scan.current_beam_az)
        assert scan.is_illuminated(scan.current_beam_az + 1.0)  # within 1.5 deg

    def test_is_illuminated_outside_beam(self, scan: ScanController) -> None:
        assert not scan.is_illuminated(scan.current_beam_az + 10.0)

    def test_scan_period(self, scan: ScanController) -> None:
        expected = 2 * 120.0 / 60.0  # 4 seconds
        np.testing.assert_allclose(scan.scan_period, expected)

    def test_dwell_time(self, scan: ScanController) -> None:
        expected = 3.0 / 60.0  # 50 ms
        np.testing.assert_allclose(scan.dwell_time, expected)


# ── Association tests ─────────────────────────────────────────────────


class TestAssociator:
    @pytest.fixture
    def associator(self) -> Associator:
        return Associator(gate_threshold=9.21)

    def _make_track(self, x: float, y: float) -> "Track":
        from radar_sim.modes.tws.track_manager import Track
        state = np.array([x, 0.0, y, 0.0])
        P = np.diag([500.0**2, 100.0**2, 500.0**2, 100.0**2])
        R = np.diag([150.0**2, np.radians(3.0)**2])
        ekf = EKFTracker(state, P, 100.0, R)
        return Track(
            track_id="T001", ekf=ekf, status=TrackStatus.TENTATIVE,
        )

    def test_exact_match_associates(self, associator: Associator) -> None:
        trk = self._make_track(1000.0, 20000.0)
        r = np.sqrt(1000**2 + 20000**2)
        az = np.degrees(np.arctan2(1000, 20000))
        det = Detection(range_m=r, azimuth_deg=az)
        result = associator.associate([trk], [det])
        assert len(result.associated) == 1
        assert len(result.unassociated_detections) == 0

    def test_far_detection_does_not_associate(self, associator: Associator) -> None:
        trk = self._make_track(1000.0, 20000.0)
        det = Detection(range_m=50000.0, azimuth_deg=45.0)
        result = associator.associate([trk], [det])
        assert len(result.associated) == 0
        assert len(result.unassociated_detections) == 1
        assert len(result.unassociated_tracks) == 1

    def test_empty_inputs(self, associator: Associator) -> None:
        result = associator.associate([], [])
        assert len(result.associated) == 0


# ── Track manager tests ──────────────────────────────────────────────


class TestTrackManager:
    @pytest.fixture
    def tm(self) -> TrackManager:
        R = np.diag([150.0**2, np.radians(3.0)**2])
        return TrackManager(confirm_m=3, confirm_n=5, max_coast=5, R_meas=R)

    def test_initiate_creates_tentative_track(self, tm: TrackManager) -> None:
        trk = tm.initiate_track(1000.0, 20000.0, time=0.0)
        assert trk.status == TrackStatus.TENTATIVE
        assert len(tm.tracks) == 1

    def test_m_of_n_confirmation(self, tm: TrackManager) -> None:
        trk = tm.initiate_track(1000.0, 20000.0, time=0.0)
        r = np.sqrt(1000**2 + 20000**2)
        az = np.arctan2(1000, 20000)
        # 2 more updates → 3 total hits → confirmed
        tm.update_track(trk, r, az, time=1.0)
        assert trk.status == TrackStatus.TENTATIVE
        tm.update_track(trk, r, az, time=2.0)
        assert trk.status == TrackStatus.CONFIRMED

    def test_coast_then_drop(self, tm: TrackManager) -> None:
        trk = tm.initiate_track(1000.0, 20000.0, time=0.0)
        r = np.sqrt(1000**2 + 20000**2)
        az = np.arctan2(1000, 20000)
        # Confirm it first
        for i in range(3):
            tm.update_track(trk, r, az, time=float(i))
        assert trk.status == TrackStatus.CONFIRMED
        # Coast 5 times → dropped
        for _ in range(5):
            tm.coast_track(trk)
        assert trk.status == TrackStatus.DROPPED

    def test_prune_removes_dropped(self, tm: TrackManager) -> None:
        trk = tm.initiate_track(1000.0, 20000.0, time=0.0)
        for _ in range(5):
            tm.coast_track(trk)
        dropped = tm.prune_dropped()
        assert len(dropped) == 1
        assert len(tm.tracks) == 0


# ── Integration tests ─────────────────────────────────────────────────


class TestTWSIntegration:
    def test_tws_produces_detections_after_multiple_scans(self) -> None:
        """Run TWS for several scan periods and expect confirmed tracks."""
        np.random.seed(42)
        from radar_sim.engine import SimulationEngine
        from radar_sim.models import RadarMode, ClutterParams

        engine = SimulationEngine(clutter=ClutterParams(enabled=False))
        engine.set_mode(RadarMode.TWS)

        # Run for 20 seconds at 50 ms steps (enough for ~5 full scan periods)
        for _ in range(400):
            frame = engine.tick(dt=0.05)

        # After 20s of scanning, TWS should have some confirmed tracks
        tws = engine._modes[RadarMode.TWS]
        confirmed = tws.track_manager.get_confirmed_tracks()
        assert len(confirmed) >= 1

    def test_tws_no_false_tracks_from_clutter(self) -> None:
        """With clutter disabled, all tracks should correspond to real targets."""
        np.random.seed(42)
        from radar_sim.engine import SimulationEngine
        from radar_sim.models import RadarMode, ClutterParams

        engine = SimulationEngine(clutter=ClutterParams(enabled=False))
        engine.set_mode(RadarMode.TWS)

        for _ in range(400):
            engine.tick(dt=0.05)

        tws = engine._modes[RadarMode.TWS]
        confirmed = tws.track_manager.get_confirmed_tracks()
        # Should not exceed the number of targets in default scenario (5)
        assert len(confirmed) <= 5

    def test_tws_mode_name(self) -> None:
        mode = TWSMode(RadarParams())
        assert "TWS" in mode.name
        assert len(mode.description) > 0
