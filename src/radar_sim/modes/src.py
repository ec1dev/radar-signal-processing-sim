"""
SRC (Search) Mode — the simplest radar mode.

Just range-gates the returns and applies an SNR threshold.
No Doppler processing, no clutter rejection.
What you see is what you get — targets AND clutter.
"""

import numpy as np
from radar_sim.models import RawReturn, Detection, RadarParams
from radar_sim.modes.base_mode import BaseMode


class SRCMode(BaseMode):
    """
    Search mode: amplitude vs range, threshold detection.

    This is the baseline "dumb" mode:
    - Groups returns into range bins
    - Computes total power per bin (signal + clutter + noise)
    - Detects anything above threshold
    - Cannot distinguish targets from clutter

    The user will see: everything lights up, especially at close range
    where clutter is strong. Targets buried in clutter are missed.
    """

    @property
    def name(self) -> str:
        return "SRC (Search)"

    @property
    def description(self) -> str:
        return "Basic range-gated search. No clutter rejection — shows everything."

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        detections = []
        noise_power = self.radar.noise_power
        threshold_linear = 10 ** (self.radar.detection_threshold_db / 10)

        # Group returns into range bins
        range_res = self.radar.range_resolution
        max_range = self.radar.max_unambiguous_range

        # Build range bins
        num_bins = int(max_range / range_res)
        bin_power = np.zeros(num_bins)         # total power per bin
        bin_target_ids: list[list] = [[] for _ in range(num_bins)]
        bin_has_clutter = [False] * num_bins

        for ret in raw_returns:
            bin_idx = int(ret.range_m / range_res)
            if 0 <= bin_idx < num_bins:
                bin_power[bin_idx] += ret.received_power
                if ret.target_id is not None:
                    bin_target_ids[bin_idx].append(ret.target_id)
                if ret.is_clutter:
                    bin_has_clutter[bin_idx] = True

        # Detection: compare each bin's power against noise floor * threshold
        for i in range(num_bins):
            total_power = bin_power[i] + noise_power  # signal + noise
            snr = total_power / noise_power

            if snr >= threshold_linear:
                range_m = (i + 0.5) * range_res  # center of bin

                # Determine if this is a "real" target or just clutter
                # SRC can't tell the difference — that's the whole point
                target_id = bin_target_ids[i][0] if bin_target_ids[i] else None
                is_clutter = bin_has_clutter[i] and not bin_target_ids[i]

                detections.append(Detection(
                    range_m=range_m,
                    velocity_mps=None,  # SRC doesn't measure velocity
                    snr_db=10 * np.log10(snr),
                    target_id=target_id,
                    is_clutter=is_clutter,
                ))

        return detections
