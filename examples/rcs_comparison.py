"""
Detection range vs RCS -- how stealth changes the equation.

Computes the maximum detection range for targets with different radar
cross-sections using the radar range equation, showing how a 60 dB
RCS reduction (B-52 to F-22) translates to a ~10x range reduction.

Usage:
    python -m examples.rcs_comparison
"""

import numpy as np
from radar_sim.models import RadarParams, C, K_BOLTZ
from radar_sim.scenario.rcs_database import RCS_DATABASE


def max_detection_range(radar: RadarParams, rcs: float) -> float:
    """Compute max detection range (m) for a given RCS using the radar equation."""
    snr_required = 10 ** (radar.detection_threshold_db / 10)
    numerator = (
        radar.power * radar.gain_linear**2 * radar.wavelength**2 * rcs
    )
    denominator = (4 * np.pi)**3 * radar.noise_power * snr_required
    return float((numerator / denominator) ** 0.25)


def main() -> None:
    radar = RadarParams()

    print("=" * 66)
    print("DETECTION RANGE vs RADAR CROSS-SECTION")
    print("=" * 66)
    print(f"Radar: X-band {radar.frequency/1e9:.0f} GHz | "
          f"Power: {radar.power/1000:.0f} kW | "
          f"Gain: {radar.gain_db:.0f} dBi | "
          f"Threshold: {radar.detection_threshold_db:.0f} dB")
    print()

    targets = [
        ("B-52 (bomber)", "B-52"),
        ("Su-27 (fighter)", "Su-27"),
        ("F-16 (fighter)", "F-16"),
        ("Cruise missile", "Cruise missile"),
        ("Su-57 (reduced RCS)", "Su-57"),
        ("F-35 (stealth)", "F-35"),
        ("F-22 (stealth)", "F-22"),
    ]

    print(f"  {'Aircraft':<24s} | {'RCS':>10s} | {'Max Range':>10s} | {'RCS (dBsm)':>10s}")
    print(f"  {'-'*24} | {'-'*10} | {'-'*10} | {'-'*10}")
    for label, key in targets:
        rcs = RCS_DATABASE[key]
        r = max_detection_range(radar, rcs)
        rcs_db = 10 * np.log10(rcs)
        print(f"  {label:<24s} | {rcs:>8.4f} m2 | {r/1000:>8.1f} km | {rcs_db:>+8.1f} dBsm")

    print()
    print("Stealth reduces detection range by the fourth root of RCS reduction.")
    print(f"A B-52 (100 m2) is detectable at {max_detection_range(radar, 100)/1000:.0f} km.")
    print(f"An F-22 (0.0001 m2) is detectable at {max_detection_range(radar, 0.0001)/1000:.1f} km.")
    print(f"That's a {max_detection_range(radar, 100)/max_detection_range(radar, 0.0001):.0f}x range reduction.")


if __name__ == "__main__":
    main()
