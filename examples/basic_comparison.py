"""
Three-way mode comparison: SRC vs MTI vs Pulse Doppler.

Runs the default scenario (5 airborne targets + ground clutter) through
all three processing modes and prints a side-by-side comparison showing
detection counts, clutter false alarms, and velocity measurement capability.

Usage:
    python -m examples.basic_comparison
"""

import numpy as np

from radar_sim.models import RadarMode
from radar_sim.engine import SimulationEngine


def main() -> None:
    np.random.seed(42)
    engine = SimulationEngine()

    # ── Ground truth ─────────────────────────────────────────────────
    frame = engine.tick(dt=0.0)
    print("=" * 72)
    print("RADAR SIGNAL PROCESSING SIMULATOR — MODE COMPARISON")
    print("=" * 72)
    print(f"\nRadar: {frame.radar_params_summary['frequency_ghz']:.1f} GHz  "
          f"PRF={frame.radar_params_summary['prf_hz']:.0f} Hz  "
          f"R_max={frame.radar_params_summary['max_unamb_range_km']:.1f} km")

    print(f"\nGround truth ({len(frame.targets)} targets):")
    print(f"  {'ID':8s} | {'Label':15s} | {'Range':>9s} | {'Vr':>8s} | {'RCS':>6s}")
    print(f"  {'-'*8} | {'-'*15} | {'-'*9} | {'-'*8} | {'-'*6}")
    for t in frame.targets:
        print(f"  {t['id']:8s} | {t['label']:15s} | "
              f"{t['range_m']/1000:7.1f} km | "
              f"{t['radial_velocity']:6.1f} m/s | "
              f"{t['rcs']:4.1f} m\u00b2")

    # ── Run each mode ────────────────────────────────────────────────
    results: dict[str, dict] = {}
    for mode_enum in [RadarMode.SRC, RadarMode.MTI, RadarMode.PULSE_DOPPLER]:
        np.random.seed(42)
        engine2 = SimulationEngine()
        engine2.set_mode(mode_enum)
        f = engine2.tick(dt=0.0)

        target_dets = [d for d in f.detections if d.target_id is not None]
        clutter_dets = [d for d in f.detections if d.is_clutter]
        ambiguous = [d for d in f.detections if d.is_ambiguous]
        det_ids = sorted({d.target_id for d in target_dets})

        results[f.mode] = {
            "mode_name": f.mode,
            "total": len(f.detections),
            "targets": len(det_ids),
            "clutter": len(clutter_dets),
            "ambiguous": len(ambiguous),
            "det_ids": det_ids,
            "has_velocity": any(d.velocity_mps is not None for d in target_dets),
            "target_dets": target_dets,
        }

        print(f"\n{'=' * 72}")
        print(f"  {f.mode}")
        print(f"{'=' * 72}")
        print(f"  Total detections: {len(f.detections)}")
        print(f"  Target detections: {len(target_dets)}  |  "
              f"Clutter false alarms: {len(clutter_dets)}")
        if target_dets:
            for d in target_dets[:8]:
                v_str = f"V={d.velocity_mps:7.1f} m/s" if d.velocity_mps is not None else "V=      N/A"
                amb = " [AMBIGUOUS]" if d.is_ambiguous else ""
                print(f"    {d.target_id:8s} | R={d.range_m/1000:7.1f} km | "
                      f"{v_str} | SNR={d.snr_db:5.1f} dB{amb}")
            if len(target_dets) > 8:
                print(f"    ... and {len(target_dets) - 8} more")

    # ── Summary table ────────────────────────────────────────────────
    print(f"\n{'=' * 72}")
    print("COMPARISON SUMMARY")
    print(f"{'=' * 72}")
    names = list(results.keys())
    print(f"  {'Metric':<28s}", end="")
    for n in names:
        print(f" | {n:>18s}", end="")
    print()
    print(f"  {'-'*28}", end="")
    for _ in names:
        print(f" | {'-'*18}", end="")
    print()

    rows = [
        ("Targets detected (of 5)", lambda r: str(r["targets"])),
        ("Clutter false alarms", lambda r: str(r["clutter"])),
        ("Velocity measurement", lambda r: "Yes" if r["has_velocity"] else "No"),
        ("Detected IDs", lambda r: ", ".join(r["det_ids"])[:18]),
    ]
    for label, fn in rows:
        print(f"  {label:<28s}", end="")
        for n in names:
            print(f" | {fn(results[n]):>18s}", end="")
        print()


if __name__ == "__main__":
    main()
