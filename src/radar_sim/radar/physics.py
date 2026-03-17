"""
Physics engine: given the radar and scenario, compute raw returns.
This is the abstract model — no waveform generation, just radar equation + geometry.
"""

import numpy as np
from radar_sim.models import (
    Target, RadarParams, RadarPosition, ClutterParams,
    RawReturn, C, K_BOLTZ
)


class PhysicsEngine:
    """
    Computes raw returns from targets and clutter using the radar range equation.
    Abstract model: directly computes received power, Doppler shift, range.
    No actual waveform generation — that comes later for pulse Doppler.
    """

    def __init__(self, radar: RadarParams, position: RadarPosition, clutter: ClutterParams):
        self.radar = radar
        self.position = position
        self.clutter = clutter

    def compute_target_return(self, target: Target) -> RawReturn | None:
        """
        Compute the raw return from a single target.
        Returns None if target is behind the radar or out of geometry.
        """
        # Relative position
        dx = target.x - self.position.x
        dy = target.y - self.position.y
        dz = target.altitude - self.position.altitude

        # Slant range
        range_m = np.sqrt(dx**2 + dy**2 + dz**2)

        if range_m < 1.0:  # avoid division by zero
            return None

        # Unit vector from radar to target
        ux, uy, uz = dx / range_m, dy / range_m, dz / range_m

        # Radial velocity (positive = closing = target moving toward radar)
        # Dot product of target velocity with unit vector FROM target TO radar
        radial_velocity = -(target.vx * ux + target.vy * uy)
        # (negative because ux,uy points radar→target, and closing means
        #  target velocity opposes that direction)

        # Doppler shift: f_d = 2 * v_r / λ (positive = closing)
        doppler_hz = 2 * radial_velocity / self.radar.wavelength

        # Received power via radar range equation:
        # Pr = (Pt * G^2 * λ^2 * σ) / ((4π)^3 * R^4)
        numerator = (
            self.radar.power
            * self.radar.gain_linear**2
            * self.radar.wavelength**2
            * target.rcs
        )
        denominator = (4 * np.pi)**3 * range_m**4

        received_power = numerator / denominator

        # Azimuth: angle from north (radar heading), east positive
        azimuth_rad = np.arctan2(dx, dy) - self.position.heading
        azimuth_deg = float(np.degrees(azimuth_rad))

        return RawReturn(
            range_m=range_m,
            radial_velocity=radial_velocity,
            received_power=received_power,
            doppler_hz=doppler_hz,
            azimuth_deg=azimuth_deg,
            target_id=target.id,
            is_clutter=False,
        )

    def compute_clutter_returns(self, max_range: float | None = None,
                                 num_cells: int = 200) -> list[RawReturn]:
        """
        Generate clutter returns across range cells.

        Simple model: ground clutter at each range cell with power determined by
        terrain reflectivity, illuminated area, and radar equation.
        Clutter has ~zero radial velocity (stationary ground).
        """
        if not self.clutter.enabled:
            return []

        if max_range is None:
            max_range = self.radar.max_unambiguous_range

        clutter_returns = []
        range_cells = np.linspace(
            self.radar.range_resolution,  # start at first range cell
            max_range,
            num_cells
        )

        for r in range_cells:
            # Simplified clutter model:
            # Clutter RCS per cell ≈ σ_0 * A_cell
            # where A_cell ≈ range_resolution * r * beamwidth_az
            # and σ_0 is terrain reflectivity (m^2/m^2)
            beamwidth_rad = np.radians(self.radar.beamwidth_az)
            cell_area = self.radar.range_resolution * r * beamwidth_rad
            clutter_rcs = self.clutter.reflectivity_linear * cell_area

            # Radar equation for this clutter cell
            numerator = (
                self.radar.power
                * self.radar.gain_linear**2
                * self.radar.wavelength**2
                * clutter_rcs
            )
            denominator = (4 * np.pi)**3 * r**4
            clutter_power = numerator / denominator

            # Clutter has zero radial velocity (stationary)
            # In practice there's clutter spread from wind, platform motion, etc.
            # We add a tiny random velocity to make it slightly non-ideal
            clutter_vel = np.random.normal(0, 0.5)  # small spread, m/s
            clutter_doppler = 2 * clutter_vel / self.radar.wavelength

            # Distribute clutter across the full scan volume for display.
            # In a real radar, clutter appears wherever the beam points during
            # a scan.  We model this as uniform azimuth across ±45 degrees.
            clutter_az = np.random.uniform(-45.0, 45.0)

            clutter_returns.append(RawReturn(
                range_m=r,
                radial_velocity=clutter_vel,
                received_power=clutter_power,
                doppler_hz=clutter_doppler,
                azimuth_deg=clutter_az,
                target_id=None,
                is_clutter=True,
            ))

        return clutter_returns

    def compute_all_returns(self, targets: list[Target]) -> list[RawReturn]:
        """
        Compute raw returns from all targets + clutter.
        This is what gets fed to the radar mode processor.
        """
        returns = []

        # Target returns
        for target in targets:
            ret = self.compute_target_return(target)
            if ret is not None:
                returns.append(ret)

        # Clutter returns
        returns.extend(self.compute_clutter_returns())

        # Add thermal noise floor info to each return
        # (The mode processor will use radar.noise_power for detection decisions)

        return returns

    def compute_snr(self, raw_return: RawReturn) -> float:
        """Compute SNR in dB for a single return."""
        if raw_return.received_power <= 0:
            return -np.inf
        return 10 * np.log10(raw_return.received_power / self.radar.noise_power)

    def compute_scr(self, target_return: RawReturn,
                    clutter_returns: list[RawReturn]) -> float:
        """
        Compute signal-to-clutter ratio (dB) for a target.
        Sums clutter power in the same range cell as the target.
        """
        range_res = self.radar.range_resolution
        competing_clutter = sum(
            c.received_power for c in clutter_returns
            if abs(c.range_m - target_return.range_m) < range_res
        )
        if competing_clutter <= 0:
            return np.inf
        return 10 * np.log10(target_return.received_power / competing_clutter)
