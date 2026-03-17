"""
Track lifecycle management for TWS mode.

Manages the creation, confirmation, coasting, and deletion of tracks
using an M-of-N confirmation rule.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from radar_sim.modes.tws.ekf_tracker import EKFTracker


class TrackStatus(Enum):
    TENTATIVE = "tentative"
    CONFIRMED = "confirmed"
    COASTING = "coasting"
    DROPPED = "dropped"


@dataclass
class Track:
    """A single tracked object."""
    track_id: str
    ekf: EKFTracker
    status: TrackStatus
    hits: int = 1
    misses: int = 0
    total_updates: int = 1   # beam passes over this track's azimuth
    last_update_time: float = 0.0
    creation_time: float = 0.0


class TrackManager:
    """
    Manages the track lifecycle using an M-of-N confirmation rule.

    Parameters
    ----------
    confirm_m : int
        Minimum hits required within the first *confirm_n* scan opportunities
        to promote a track to CONFIRMED.
    confirm_n : int
        Window of scan opportunities for the confirmation rule.
    max_coast : int
        Maximum consecutive misses before a track is DROPPED.
    process_noise_q : float
        Forwarded to newly created EKF instances.
    R_meas : ndarray
        Measurement noise covariance forwarded to new EKFs.
    init_pos_var : float
        Initial position variance for new tracks (m^2).
    init_vel_var : float
        Initial velocity variance for new tracks (m/s)^2.
    """

    def __init__(
        self,
        confirm_m: int = 3,
        confirm_n: int = 5,
        max_coast: int = 5,
        process_noise_q: float = 100.0,
        R_meas: np.ndarray | None = None,
        init_pos_var: float = 500.0**2,
        init_vel_var: float = 100.0**2,
    ):
        self.confirm_m = confirm_m
        self.confirm_n = confirm_n
        self.max_coast = max_coast
        self._q = process_noise_q
        self._R = R_meas if R_meas is not None else np.diag([150.0**2, np.radians(3.0)**2])
        self._init_pos_var = init_pos_var
        self._init_vel_var = init_vel_var
        self.tracks: list[Track] = []
        self._next_id: int = 1

    # ── track creation ────────────────────────────────────────────────

    def initiate_track(
        self,
        x_pos: float, y_pos: float,
        time: float,
    ) -> Track:
        """Create a new TENTATIVE track from an unassociated detection."""
        state = np.array([x_pos, 0.0, y_pos, 0.0])
        P = np.diag([
            self._init_pos_var, self._init_vel_var,
            self._init_pos_var, self._init_vel_var,
        ])
        ekf = EKFTracker(state, P, self._q, self._R)
        track = Track(
            track_id=f"T{self._next_id:03d}",
            ekf=ekf,
            status=TrackStatus.TENTATIVE,
            hits=1,
            misses=0,
            total_updates=1,
            last_update_time=time,
            creation_time=time,
        )
        self._next_id += 1
        self.tracks.append(track)
        return track

    # ── track update / coast ──────────────────────────────────────────

    def update_track(
        self,
        track: Track,
        z_range: float,
        z_azimuth_rad: float,
        time: float,
    ) -> None:
        """Apply a correlated measurement to an existing track."""
        track.ekf.update(z_range, z_azimuth_rad)
        track.hits += 1
        track.misses = 0
        track.total_updates += 1
        track.last_update_time = time
        self._evaluate_status(track)

    def coast_track(self, track: Track) -> None:
        """Mark a track as missed on this scan opportunity (predict only)."""
        track.misses += 1
        track.total_updates += 1
        if track.misses >= self.max_coast:
            track.status = TrackStatus.DROPPED
        elif track.status == TrackStatus.CONFIRMED:
            track.status = TrackStatus.COASTING

    # ── prediction ────────────────────────────────────────────────────

    def predict_all(self, dt: float) -> None:
        """Predict all active tracks forward by *dt* seconds."""
        for track in self.tracks:
            if track.status != TrackStatus.DROPPED:
                track.ekf.predict(dt)

    # ── lifecycle evaluation ──────────────────────────────────────────

    def _evaluate_status(self, track: Track) -> None:
        """Promote or demote a track based on the M-of-N rule."""
        if track.status == TrackStatus.DROPPED:
            return
        if track.hits >= self.confirm_m:
            track.status = TrackStatus.CONFIRMED
        elif track.total_updates >= self.confirm_n and track.hits < self.confirm_m:
            track.status = TrackStatus.DROPPED

    # ── queries ───────────────────────────────────────────────────────

    def prune_dropped(self) -> list[Track]:
        """Remove and return DROPPED tracks."""
        dropped = [t for t in self.tracks if t.status == TrackStatus.DROPPED]
        self.tracks = [t for t in self.tracks if t.status != TrackStatus.DROPPED]
        return dropped

    def get_active_tracks(self) -> list[Track]:
        """All tracks except DROPPED."""
        return [t for t in self.tracks if t.status != TrackStatus.DROPPED]

    def get_confirmed_tracks(self) -> list[Track]:
        """Only CONFIRMED and COASTING tracks (reliable enough to display)."""
        return [
            t for t in self.tracks
            if t.status in (TrackStatus.CONFIRMED, TrackStatus.COASTING)
        ]
