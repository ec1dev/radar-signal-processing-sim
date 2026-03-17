"""
Radar platform comparison -- fighter vs AWACS vs ground-based.

Shows how different radar systems see the same target set using
real-world-inspired parameters for each platform.

Usage:
    python -m examples.platform_comparison
"""

import numpy as np
from radar_sim.models import RadarParams, Target


def max_detection_range(radar: RadarParams, rcs: float) -> float:
    """Max detection range (m) for a given RCS."""
    snr_req = 10 ** (radar.detection_threshold_db / 10)
    num = radar.power * radar.gain_linear**2 * radar.wavelength**2 * rcs
    den = (4 * np.pi)**3 * radar.noise_power * snr_req
    return float((num / den) ** 0.25)


PLATFORMS = {
    "AN/APG-68 (F-16)": RadarParams(
        frequency=10.0e9, power=50_000, gain_db=33.0,
        pulse_width=1e-6, prf=2000, bandwidth=1e6,
    ),
    "AN/APY-1 (E-3 AWACS)": RadarParams(
        frequency=3.0e9, power=1_000_000, gain_db=40.0,
        pulse_width=6e-6, prf=300, bandwidth=167_000,
        noise_figure_db=3.0,
    ),
    "AN/MPQ-53 (Patriot)": RadarParams(
        frequency=5.5e9, power=5_000_000, gain_db=44.0,
        pulse_width=0.5e-6, prf=1000, bandwidth=2e6,
        noise_figure_db=3.5,
    ),
}

TARGETS = [
    ("Fighter (3 m2)", 3.0),
    ("Bomber (25 m2)", 25.0),
    ("Cruise missile (0.1 m2)", 0.1),
    ("Stealth fighter (0.001 m2)", 0.001),
]


def main() -> None:
    print("=" * 72)
    print("RADAR PLATFORM COMPARISON — MAX DETECTION RANGE")
    print("=" * 72)

    for pname, radar in PLATFORMS.items():
        print(f"\n  {pname}")
        print(f"    Freq: {radar.frequency/1e9:.1f} GHz | "
              f"Power: {radar.power/1000:.0f} kW | "
              f"Gain: {radar.gain_db:.0f} dBi")
        print(f"    {'Target':<30s} | {'Max Range':>10s}")
        print(f"    {'-'*30} | {'-'*10}")
        for tname, rcs in TARGETS:
            r = max_detection_range(radar, rcs)
            print(f"    {tname:<30s} | {r/1000:>8.1f} km")

    print("\n  The AWACS sees a fighter at >500 km; the fighter radar at ~50 km.")
    print("  Stealth renders even the Patriot's 5 MW radar nearly blind at range.")


if __name__ == "__main__":
    main()
