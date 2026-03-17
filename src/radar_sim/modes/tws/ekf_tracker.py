"""
Extended Kalman Filter (EKF) for single-target state estimation.

State vector (4-D Cartesian, relative to radar position):
    x = [x_pos, x_vel, y_pos, y_vel]
        x is east (m), y is north (m), velocities in m/s.

Measurement vector (polar):
    z = [range, azimuth]
        range in metres, azimuth in radians (from north, east positive).

The measurement model is nonlinear (Cartesian → polar), which is why
this is an *Extended* Kalman Filter rather than a standard linear one.
"""

from __future__ import annotations

import numpy as np


def _wrap_angle(a: float) -> float:
    """Wrap angle to [-pi, pi)."""
    return (a + np.pi) % (2 * np.pi) - np.pi


class EKFTracker:
    """
    Constant-velocity Extended Kalman Filter with range-azimuth measurements.

    Parameters
    ----------
    state_init : ndarray, shape (4,)
        Initial state ``[x, vx, y, vy]``.
    P_init : ndarray, shape (4, 4)
        Initial covariance.
    process_noise_q : float
        Process noise spectral density (m^2/s^4).  Typical values:
        10-50 for non-maneuvering, 100-400 for maneuvering targets.
    R_meas : ndarray, shape (2, 2)
        Measurement noise covariance ``diag([sigma_r^2, sigma_az^2])``.
    """

    def __init__(
        self,
        state_init: np.ndarray,
        P_init: np.ndarray,
        process_noise_q: float,
        R_meas: np.ndarray,
    ):
        self.x: np.ndarray = np.asarray(state_init, dtype=np.float64).copy()
        self.P: np.ndarray = np.asarray(P_init, dtype=np.float64).copy()
        self._q = process_noise_q
        self.R: np.ndarray = np.asarray(R_meas, dtype=np.float64).copy()

    # ── prediction ────────────────────────────────────────────────────

    def predict(self, dt: float) -> None:
        """Propagate state and covariance forward by *dt* seconds.

        Uses a constant-velocity transition model::

            F = [[1, dt, 0,  0],
                 [0,  1, 0,  0],
                 [0,  0, 1, dt],
                 [0,  0, 0,  1]]

        Process noise follows the continuous white-noise acceleration model.
        """
        F = np.array([
            [1, dt, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, dt],
            [0, 0, 0, 1],
        ], dtype=np.float64)

        q = self._q
        dt2 = dt * dt
        dt3 = dt2 * dt
        Q = q * np.array([
            [dt3 / 3, dt2 / 2, 0, 0],
            [dt2 / 2, dt, 0, 0],
            [0, 0, dt3 / 3, dt2 / 2],
            [0, 0, dt2 / 2, dt],
        ], dtype=np.float64)

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q
        self.P = (self.P + self.P.T) / 2  # enforce symmetry

    # ── measurement model ─────────────────────────────────────────────

    @staticmethod
    def _h(state: np.ndarray) -> np.ndarray:
        """Nonlinear measurement function h(x) → [range, azimuth]."""
        x, _vx, y, _vy = state
        r = np.sqrt(x * x + y * y)
        az = np.arctan2(x, y)  # from north, east positive
        return np.array([r, az])

    @staticmethod
    def _H_jacobian(state: np.ndarray) -> np.ndarray:
        """Jacobian of h(x) with respect to the state vector."""
        x, _vx, y, _vy = state
        r = max(np.sqrt(x * x + y * y), 1.0)  # guard against zero
        r2 = r * r
        return np.array([
            [x / r, 0, y / r, 0],       # ∂r/∂state
            [y / r2, 0, -x / r2, 0],     # ∂az/∂state
        ], dtype=np.float64)

    # ── update ────────────────────────────────────────────────────────

    def update(self, z_range: float, z_azimuth: float) -> None:
        """Fuse a range-azimuth measurement using the EKF update equations.

        The azimuth innovation is wrapped to ``[-pi, pi)`` to handle the
        discontinuity at +-180 deg.  The Joseph form is used for the
        covariance update for numerical stability.
        """
        z = np.array([z_range, z_azimuth])
        z_pred = self._h(self.x)
        H = self._H_jacobian(self.x)

        # Innovation with angle wrapping on the azimuth component
        y = z - z_pred
        y[1] = _wrap_angle(y[1])

        # Innovation covariance
        S = H @ self.P @ H.T + self.R

        # Kalman gain
        K = self.P @ H.T @ np.linalg.inv(S)

        # State update
        self.x = self.x + K @ y

        # Covariance update — Joseph form for numerical stability:
        #   P = (I - K H) P (I - K H)^T  +  K R K^T
        I_KH = np.eye(4) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ self.R @ K.T
        self.P = (self.P + self.P.T) / 2  # enforce symmetry

    # ── convenience properties ────────────────────────────────────────

    @property
    def position(self) -> tuple[float, float]:
        """Estimated (x_east, y_north) position in metres."""
        return float(self.x[0]), float(self.x[2])

    @property
    def velocity(self) -> tuple[float, float]:
        """Estimated (vx_east, vy_north) velocity in m/s."""
        return float(self.x[1]), float(self.x[3])

    @property
    def position_uncertainty(self) -> float:
        """RMS position uncertainty: sqrt(sigma_x^2 + sigma_y^2)."""
        return float(np.sqrt(self.P[0, 0] + self.P[2, 2]))

    def predicted_measurement(self) -> np.ndarray:
        """Current predicted measurement [range, azimuth] for gating."""
        return self._h(self.x)

    def innovation_covariance(self) -> np.ndarray:
        """S = H P H^T + R — needed for gating."""
        H = self._H_jacobian(self.x)
        return H @ self.P @ H.T + self.R
