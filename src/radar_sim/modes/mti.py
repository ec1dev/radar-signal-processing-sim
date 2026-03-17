"""
MTI (Moving Target Indication) Mode.

Cancels stationary clutter by subtracting successive pulse returns.
The key tradeoff: clutter goes away, but targets at "blind speeds"
(velocity = n * λ * PRF / 2) also disappear.

This is the dramatic mode — users will see targets literally vanish
when their radial velocity hits a blind speed.
"""

import numpy as np
from radar_sim.models import RawReturn, Detection, RadarParams
from radar_sim.modes.base_mode import BaseMode


class MTIMode(BaseMode):
    """
    Moving Target Indication: 2-pulse canceller (abstract model).

    How it works conceptually:
    - Subtract return from pulse N from return at pulse N+1
    - Stationary objects cancel out (same phase both pulses)
    - Moving objects have a phase difference proportional to their Doppler

    The improvement factor (how much clutter is suppressed) depends on
    the target's Doppler frequency relative to PRF.

    Abstract model: we compute the MTI filter response for each return's
    Doppler frequency and apply it as a gain factor to received power.
    """

    def __init__(self, radar: RadarParams, num_pulses: int = 2):
        super().__init__(radar)
        self.num_pulses = num_pulses  # 2-pulse or 3-pulse canceller

    @property
    def name(self) -> str:
        return f"MTI ({self.num_pulses}-pulse canceller)"

    @property
    def description(self) -> str:
        return (
            "Clutter cancellation via pulse-to-pulse subtraction. "
            "Removes stationary returns but has blind speeds."
        )

    def mti_filter_response(self, doppler_hz: float) -> float:
        """
        Compute the MTI filter response (gain) for a given Doppler frequency.

        For a 2-pulse canceller: H(f) = 2 * sin(π * f / PRF)
        For a 3-pulse canceller: H(f) = 2 * sin(π * f / PRF) squared

        The response is zero at f = 0 (clutter cancelled) and at
        f = n * PRF (blind speeds).

        Returns the power gain (|H|^2 normalized so max = 1).
        """
        normalized_freq = doppler_hz / self.radar.prf
        sin_val = np.sin(np.pi * normalized_freq)

        if self.num_pulses == 2:
            # 2-pulse canceller: |H|^2 = 4 sin^2(π f/PRF), max = 4
            power_gain = 4 * sin_val**2 / 4.0  # normalize to max=1
        elif self.num_pulses == 3:
            # 3-pulse canceller: |H|^2 = 16 sin^4(π f/PRF), max = 16
            power_gain = 16 * sin_val**4 / 16.0
        else:
            power_gain = (2 * abs(sin_val))**(2 * (self.num_pulses - 1))
            max_gain = 2**(2 * (self.num_pulses - 1))
            power_gain /= max_gain

        return power_gain

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        detections = []
        noise_power = self.radar.noise_power
        threshold_linear = 10 ** (self.radar.detection_threshold_db / 10)
        range_res = self.radar.range_resolution
        max_range = self.radar.max_unambiguous_range

        # Build range bins with MTI-filtered power
        num_bins = int(max_range / range_res)
        bin_power = np.zeros(num_bins)
        bin_target_ids: list[list] = [[] for _ in range(num_bins)]
        bin_velocities: list[list] = [[] for _ in range(num_bins)]
        bin_azimuths: list[list[float]] = [[] for _ in range(num_bins)]

        for ret in raw_returns:
            bin_idx = int(ret.range_m / range_res)
            if 0 <= bin_idx < num_bins:
                # Apply MTI filter response to this return's power
                mti_gain = self.mti_filter_response(ret.doppler_hz)
                filtered_power = ret.received_power * mti_gain

                bin_power[bin_idx] += filtered_power
                bin_azimuths[bin_idx].append(ret.azimuth_deg)

                if ret.target_id is not None:
                    bin_target_ids[bin_idx].append(ret.target_id)
                    bin_velocities[bin_idx].append(ret.radial_velocity)

        # Detection
        for i in range(num_bins):
            total_power = bin_power[i] + noise_power
            snr = total_power / noise_power

            if snr >= threshold_linear:
                range_m = (i + 0.5) * range_res
                target_id = bin_target_ids[i][0] if bin_target_ids[i] else None

                # MTI doesn't give precise velocity, but we know there's motion
                velocity = bin_velocities[i][0] if bin_velocities[i] else None

                azimuth = bin_azimuths[i][0] if bin_azimuths[i] else 0.0

                detections.append(Detection(
                    range_m=range_m,
                    azimuth_deg=azimuth,
                    velocity_mps=velocity,
                    snr_db=10 * np.log10(snr),
                    target_id=target_id,
                    is_clutter=False,  # MTI filtered out clutter
                ))

        return detections
