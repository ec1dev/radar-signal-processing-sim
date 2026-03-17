"""
Detection-to-track association for TWS mode.

Uses Mahalanobis-distance gating followed by greedy nearest-neighbour
assignment.  The gating threshold is a chi-squared value for the
2-DOF measurement space (range, azimuth).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from radar_sim.models import Detection
from radar_sim.modes.tws.track_manager import Track


@dataclass
class AssociationResult:
    """Output of the association step."""
    associated: list[tuple[Track, Detection]]
    unassociated_detections: list[Detection]
    unassociated_tracks: list[Track]


def _wrap_angle(a: float) -> float:
    return (a + np.pi) % (2 * np.pi) - np.pi


class Associator:
    """
    Nearest-neighbour association with Mahalanobis gating.

    Parameters
    ----------
    gate_threshold : float
        Chi-squared gate threshold.  For 2-DOF measurements:
        9.21 → 99 % gate, 5.99 → 95 % gate.
    """

    def __init__(self, gate_threshold: float = 9.21):
        self.gate_threshold = gate_threshold

    def associate(
        self,
        tracks: list[Track],
        detections: list[Detection],
        radar_x: float = 0.0,
        radar_y: float = 0.0,
    ) -> AssociationResult:
        """
        Match detections to tracks using gated nearest-neighbour.

        Each detection is converted to ``[range, azimuth_rad]`` and compared
        against each track's predicted measurement via the Mahalanobis
        distance.  Pairs within the gate are assigned greedily (smallest
        distance first).
        """
        if not tracks or not detections:
            return AssociationResult(
                associated=[],
                unassociated_detections=list(detections),
                unassociated_tracks=list(tracks),
            )

        # Convert detections to measurement vectors [range, azimuth_rad]
        det_meas: list[np.ndarray] = []
        for d in detections:
            az_rad = np.radians(d.azimuth_deg)
            det_meas.append(np.array([d.range_m, az_rad]))

        # Build cost matrix: (n_tracks, n_detections)
        n_t = len(tracks)
        n_d = len(detections)
        cost = np.full((n_t, n_d), np.inf)

        for ti, trk in enumerate(tracks):
            z_pred = trk.ekf.predicted_measurement()
            S = trk.ekf.innovation_covariance()
            S_inv = np.linalg.inv(S)

            for di, z in enumerate(det_meas):
                innov = z - z_pred
                innov[1] = _wrap_angle(innov[1])
                dist = float(innov @ S_inv @ innov)
                if dist < self.gate_threshold:
                    cost[ti, di] = dist

        # Greedy nearest-neighbour assignment
        assigned_tracks: set[int] = set()
        assigned_dets: set[int] = set()
        associated: list[tuple[Track, Detection]] = []

        # Flatten and sort by cost
        indices = np.argwhere(np.isfinite(cost))
        if indices.size > 0:
            costs = cost[indices[:, 0], indices[:, 1]]
            order = np.argsort(costs)
            for idx in order:
                ti, di = int(indices[idx, 0]), int(indices[idx, 1])
                if ti not in assigned_tracks and di not in assigned_dets:
                    associated.append((tracks[ti], detections[di]))
                    assigned_tracks.add(ti)
                    assigned_dets.add(di)

        unassoc_det = [d for i, d in enumerate(detections) if i not in assigned_dets]
        unassoc_trk = [t for i, t in enumerate(tracks) if i not in assigned_tracks]

        return AssociationResult(
            associated=associated,
            unassociated_detections=unassoc_det,
            unassociated_tracks=unassoc_trk,
        )
