"""
Clutter rejection comparison across all three modes.

Demonstrates how SRC drowns in clutter, MTI eliminates it via pulse
cancellation, and Pulse Doppler rejects it with a spectral notch + CFAR.

Usage:
    python -m examples.clutter_rejection
"""

import numpy as np

from radar_sim.models import RadarParams, RadarMode
from radar_sim.engine import SimulationEngine


def run_mode(mode: RadarMode, seed: int = 42, **radar_kwargs) -> dict:
    """Run a single mode and return detection stats."""
    np.random.seed(seed)
    radar = RadarParams(**radar_kwargs) if radar_kwargs else RadarParams()
    engine = SimulationEngine(radar=radar)
    engine.set_mode(mode)
    frame = engine.tick(dt=0.0)

    target_dets = [d for d in frame.detections if d.target_id is not None]
    clutter_dets = [d for d in frame.detections if d.is_clutter]
    return {
        "mode": frame.mode,
        "total": len(frame.detections),
        "targets": len({d.target_id for d in target_dets}),
        "clutter": len(clutter_dets),
    }


def main() -> None:
    print("=" * 72)
    print("CLUTTER REJECTION COMPARISON")
    print("=" * 72)

    modes = [RadarMode.SRC, RadarMode.MTI, RadarMode.PULSE_DOPPLER]
    results = [run_mode(m) for m in modes]

    print(f"\n  {'Mode':<30s} | {'Targets':>8s} | {'Clutter FA':>10s} | {'Total':>6s}")
    print(f"  {'-'*30} | {'-'*8} | {'-'*10} | {'-'*6}")
    for r in results:
        print(f"  {r['mode']:<30s} | {r['targets']:>8d} | {r['clutter']:>10d} | {r['total']:>6d}")

    src_clutter = results[0]["clutter"]
    if src_clutter > 0:
        print(f"\n  Clutter improvement factor (vs SRC baseline of {src_clutter}):")
        for r in results[1:]:
            if r["clutter"] == 0:
                print(f"    {r['mode']:<30s}: infinite (0 false alarms)")
            else:
                factor = src_clutter / r["clutter"]
                print(f"    {r['mode']:<30s}: {factor:.0f}x reduction "
                      f"({r['clutter']} false alarms)")

    # ── Show effect of lowering threshold ─────────────────────────────
    print(f"\n{'=' * 72}")
    print("EFFECT OF LOWERING DETECTION THRESHOLD")
    print(f"{'=' * 72}")
    print(f"\n  Lowering threshold from 13 dB to 8 dB:\n")
    print(f"  {'Mode':<30s} | {'Clutter @ 13dB':>14s} | {'Clutter @ 8dB':>13s}")
    print(f"  {'-'*30} | {'-'*14} | {'-'*13}")
    for m in modes:
        r13 = run_mode(m, detection_threshold_db=13.0)
        r8 = run_mode(m, detection_threshold_db=8.0)
        print(f"  {r13['mode']:<30s} | {r13['clutter']:>14d} | {r8['clutter']:>13d}")

    print(f"\n  SRC floods with clutter at any threshold.")
    print(f"  MTI and PD maintain low false alarm rates even with lower thresholds.")


if __name__ == "__main__":
    main()
