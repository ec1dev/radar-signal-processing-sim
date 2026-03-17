"""
Pulse Doppler range ambiguity demonstration.

Creates targets at various multiples of the maximum unambiguous range
and shows how they fold into the unambiguous interval.

Usage:
    python -m examples.range_ambiguity_demo
"""

import numpy as np

from radar_sim.models import RadarParams, Target, RadarMode, ClutterParams, C
from radar_sim.engine import SimulationEngine
from radar_sim.scenario.world import Scenario


def main() -> None:
    np.random.seed(42)
    radar = RadarParams()
    r_unamb = radar.max_unambiguous_range

    print("=" * 72)
    print("PULSE DOPPLER RANGE AMBIGUITY DEMONSTRATION")
    print("=" * 72)
    print(f"\nR_unamb = c / (2\u00b7PRF) = {r_unamb/1000:.1f} km")
    print(f"Targets beyond this range fold: R_apparent = R_true mod R_unamb\n")

    # ── Build scenario ───────────────────────────────────────────────
    multipliers = [0.5, 0.8, 1.1, 1.5, 2.0]
    scenario = Scenario()
    for m in multipliers:
        r = m * r_unamb
        scenario.add_target(Target(
            id=f"r_{m:.1f}x", x=0, y=r, altitude=5000,
            vx=0, vy=-100, rcs=10.0,
            label=f"{m:.1f}x R_unamb",
        ))

    print(f"  {'ID':>8s} | {'True Range':>12s} | {'Folded Range':>12s} | {'Ambiguous?'}")
    print(f"  {'-'*8} | {'-'*12} | {'-'*12} | {'-'*10}")
    for t in scenario.targets:
        r_true = t.y  # simplified: target directly north
        r_folded = r_true % r_unamb
        amb = "YES" if r_true > r_unamb else "no"
        print(f"  {t.id:>8s} | {r_true/1000:10.1f} km | {r_folded/1000:10.1f} km | {amb}")

    # ── Run PD mode ──────────────────────────────────────────────────
    engine = SimulationEngine(
        scenario=scenario, clutter=ClutterParams(enabled=False),
    )
    engine.set_mode(RadarMode.PULSE_DOPPLER)
    frame = engine.tick(dt=0.0)

    target_dets = [d for d in frame.detections if d.target_id is not None]
    print(f"\nPD detections ({len(target_dets)} target detections):")
    seen_ids: set[str] = set()
    for d in target_dets:
        if d.target_id in seen_ids:
            continue
        seen_ids.add(d.target_id)
        amb = " [AMBIGUOUS]" if d.is_ambiguous else ""
        print(f"    {d.target_id:>8s} | R_detected={d.range_m/1000:7.1f} km | "
              f"V={d.velocity_mps:7.1f} m/s{amb}")

    not_detected = set(t.id for t in scenario.targets) - seen_ids
    if not_detected:
        print(f"\n  Not detected: {sorted(not_detected)}")
        print("  (Very distant targets may be too weak even with coherent gain)")


if __name__ == "__main__":
    main()
