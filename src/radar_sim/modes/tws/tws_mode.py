"""
TWS (Track-While-Scan) Mode — antenna scan + EKF multi-target tracking.

Unlike the stateless SRC/MTI/PD modes, TWS maintains persistent track
state across successive process() calls.  Each tick:
    1. The antenna beam advances across the scan volume
    2. Only returns in the current beam are processed (scan gating)
    3. Detections are associated with existing tracks
    4. Matched tracks get an EKF measurement update
    5. Unmatched detections seed new tentative tracks
    6. Unmatched tracks coast (predict only) and eventually drop
    7. Output is track-based: one Detection per confirmed track with
       EKF-smoothed position and velocity

The engine calls ``tick(dt)`` before ``process()`` on each simulation step
to advance the scan and propagate all track states forward.
"""

from __future__ import annotations

import numpy as np

from radar_sim.models import (
    RawReturn, Detection, RadarParams, RadarPosition,
)
from radar_sim.modes.base_mode import BaseMode
from radar_sim.modes.tws.scan_controller import ScanController
from radar_sim.modes.tws.track_manager import TrackManager, TrackStatus
from radar_sim.modes.tws.association import Associator


class TWSMode(BaseMode):
    """
    Track-While-Scan radar mode.

    Parameters
    ----------
    radar : RadarParams
        System parameters.
    position : RadarPosition
        Radar position for Cartesian ↔ polar conversions.
    scan_volume_deg : float
        Total azimuth scan arc.
    process_noise_q : float
        EKF process noise spectral density.
    confirm_m, confirm_n : int
        M-of-N confirmation rule for track promotion.
    max_coast : int
        Maximum consecutive misses before track is dropped.
    """

    def __init__(
        self,
        radar: RadarParams,
        position: RadarPosition | None = None,
        scan_volume_deg: float = 120.0,
        process_noise_q: float = 100.0,
        confirm_m: int = 3,
        confirm_n: int = 5,
        max_coast: int = 5,
    ):
        super().__init__(radar)
        self._position = position or RadarPosition()

        # Measurement noise: range and azimuth uncertainties
        sigma_r = radar.range_resolution
        sigma_az = np.radians(radar.beamwidth_az)
        R_meas = np.diag([sigma_r**2, sigma_az**2])

        self.scan_controller = ScanController(
            scan_volume_deg=scan_volume_deg,
            scan_rate_deg_per_s=radar.scan_rate,
            beamwidth_az_deg=radar.beamwidth_az,
        )
        self.track_manager = TrackManager(
            confirm_m=confirm_m,
            confirm_n=confirm_n,
            max_coast=max_coast,
            process_noise_q=process_noise_q,
            R_meas=R_meas,
        )
        self.associator = Associator()
        self._time: float = 0.0

    # ── BaseMode interface ────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "TWS (Track-While-Scan)"

    @property
    def description(self) -> str:
        return (
            "Antenna scan + EKF multi-target tracking. "
            "Builds and maintains tracks over multiple scan sweeps."
        )

    def tick(self, dt: float) -> None:
        """Advance internal time, scan position, and predict all tracks.

        Called by the engine before ``process()`` on each simulation step.
        """
        self._time += dt
        self.scan_controller.update(dt)
        self.track_manager.predict_all(dt)

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        """
        TWS processing pipeline.

        1. Scan-gate raw returns (keep only those in the current beam)
        2. Threshold illuminated returns to form detections
        3. Associate detections with existing tracks
        4. EKF update on matched tracks
        5. Coast unmatched tracks
        6. Initiate new tracks from unmatched detections
        7. Prune dropped tracks
        8. Output one Detection per confirmed/coasting track
        """
        # 1. Scan gating — only process returns the beam is pointed at
        illuminated = [
            r for r in raw_returns
            if self.scan_controller.is_illuminated(r.azimuth_deg)
        ]

        # 2. Simple SNR threshold on illuminated returns
        noise_power = self.radar.noise_power
        threshold_linear = 10 ** (self.radar.detection_threshold_db / 10)
        detections: list[Detection] = []
        for ret in illuminated:
            snr = (ret.received_power + noise_power) / noise_power
            if snr >= threshold_linear:
                detections.append(Detection(
                    range_m=ret.range_m,
                    azimuth_deg=ret.azimuth_deg,
                    velocity_mps=ret.radial_velocity if not ret.is_clutter else None,
                    snr_db=float(10 * np.log10(snr)),
                    target_id=ret.target_id,
                    is_clutter=ret.is_clutter,
                ))

        # 3. Associate detections with tracks
        active_tracks = self.track_manager.get_active_tracks()
        result = self.associator.associate(
            active_tracks, detections,
            radar_x=self._position.x, radar_y=self._position.y,
        )

        # 4. Update matched tracks
        for track, det in result.associated:
            az_rad = np.radians(det.azimuth_deg)
            self.track_manager.update_track(
                track, det.range_m, az_rad, self._time,
            )

        # 5. Coast unmatched tracks (only if beam was near their position)
        for track in result.unassociated_tracks:
            trk_az = np.degrees(np.arctan2(
                track.ekf.position[0] - self._position.x,
                track.ekf.position[1] - self._position.y,
            ))
            if self.scan_controller.is_illuminated(trk_az):
                self.track_manager.coast_track(track)

        # 6. Initiate new tracks from unmatched detections (non-clutter only)
        for det in result.unassociated_detections:
            if det.is_clutter:
                continue
            # Convert polar detection to Cartesian relative to radar
            az_rad = np.radians(det.azimuth_deg)
            x = det.range_m * np.sin(az_rad) + self._position.x
            y = det.range_m * np.cos(az_rad) + self._position.y
            self.track_manager.initiate_track(x, y, self._time)

        # 7. Prune dropped tracks
        self.track_manager.prune_dropped()

        # 8. Build output detections from confirmed tracks
        output: list[Detection] = []
        for track in self.track_manager.get_confirmed_tracks():
            tx, ty = track.ekf.position
            vx, vy = track.ekf.velocity
            dx = tx - self._position.x
            dy = ty - self._position.y
            r = np.sqrt(dx**2 + dy**2)
            az = np.degrees(np.arctan2(dx, dy))

            # Radial velocity projection
            if r > 1.0:
                v_r = -(vx * dx / r + vy * dy / r)
            else:
                v_r = 0.0

            # Track quality: 1.0 for confirmed, decays with coasting misses
            if track.status == TrackStatus.CONFIRMED:
                quality = 1.0
            else:  # COASTING
                quality = max(0.0, 1.0 - track.misses / self.track_manager.max_coast)

            output.append(Detection(
                range_m=r,
                azimuth_deg=az,
                velocity_mps=v_r,
                snr_db=0.0,
                target_id=track.ekf.x[0],  # placeholder; ground-truth set below
                is_clutter=False,
                track_id=track.track_id,
                track_quality=quality,
            ))
            # Clear the placeholder — we don't have ground-truth mapping here
            output[-1].target_id = None

        return output
