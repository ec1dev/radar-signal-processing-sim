"""
Antenna scan pattern controller for TWS mode.

Models a mechanically or electronically scanned antenna sweeping back and
forth across a defined scan volume.  The beam position advances at a
constant angular rate and reverses direction at the scan limits.
"""

import numpy as np


class ScanController:
    """
    Raster-scan antenna model.

    The beam sweeps from ``scan_center - scan_volume/2`` to
    ``scan_center + scan_volume/2`` and back.  One full left-right-left
    traversal is one *scan period*.

    Parameters
    ----------
    scan_volume_deg : float
        Total scan arc (degrees).
    scan_rate_deg_per_s : float
        Angular sweep speed (degrees per second).
    beamwidth_az_deg : float
        Antenna 3 dB beamwidth in azimuth (degrees).
    scan_center_deg : float
        Centre of the scan volume (degrees from boresight).
    """

    def __init__(
        self,
        scan_volume_deg: float = 120.0,
        scan_rate_deg_per_s: float = 60.0,
        beamwidth_az_deg: float = 3.0,
        scan_center_deg: float = 0.0,
    ):
        self.scan_volume_deg = scan_volume_deg
        self.scan_rate = scan_rate_deg_per_s
        self.beamwidth_az = beamwidth_az_deg
        self.scan_center = scan_center_deg

        self._left_limit = scan_center_deg - scan_volume_deg / 2
        self._right_limit = scan_center_deg + scan_volume_deg / 2
        self._beam_az = self._left_limit
        self._direction = 1.0  # +1 sweeping right, -1 sweeping left
        self._completed_scans = 0

    # ── public interface ──────────────────────────────────────────────

    def update(self, dt: float) -> None:
        """Advance beam position by *dt* seconds."""
        self._beam_az += self._direction * self.scan_rate * dt

        # Reverse at scan limits
        if self._beam_az >= self._right_limit:
            self._beam_az = self._right_limit
            self._direction = -1.0
            self._completed_scans += 1
        elif self._beam_az <= self._left_limit:
            self._beam_az = self._left_limit
            self._direction = 1.0
            self._completed_scans += 1

    def is_illuminated(self, target_azimuth_deg: float) -> bool:
        """Return True if *target_azimuth_deg* falls within the current beam."""
        half_bw = self.beamwidth_az / 2
        return abs(target_azimuth_deg - self._beam_az) <= half_bw

    # ── properties ────────────────────────────────────────────────────

    @property
    def current_beam_az(self) -> float:
        """Current beam azimuth in degrees."""
        return self._beam_az

    @property
    def scan_period(self) -> float:
        """Time for one complete left-right-left sweep (seconds)."""
        return 2 * self.scan_volume_deg / self.scan_rate

    @property
    def dwell_time(self) -> float:
        """Time the beam dwells on a single resolution cell (seconds)."""
        return self.beamwidth_az / self.scan_rate

    @property
    def completed_scans(self) -> int:
        """Number of completed half-sweeps (each reversal increments)."""
        return self._completed_scans
