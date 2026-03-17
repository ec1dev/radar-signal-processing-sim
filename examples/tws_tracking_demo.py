"""
TWS (Track-While-Scan) multi-target tracking demonstration.

Runs the default scenario for multiple antenna scan periods, showing
how tracks are initiated, confirmed, and maintained via Extended
Kalman Filter updates.  Compares TWS track-based output against a
single-snapshot from the other modes.

Usage:
    python -m examples.tws_tracking_demo
"""

import numpy as np

from radar_sim.models import RadarMode, ClutterParams
from radar_sim.engine import SimulationEngine
from radar_sim.modes.tws.track_manager import TrackStatus


def main() -> None:
    np.random.seed(42)

    engine = SimulationEngine(clutter=ClutterParams(enabled=False))
    engine.set_mode(RadarMode.TWS)
    tws = engine._modes[RadarMode.TWS]

    print("=" * 72)
    print("TWS TRACKING DEMONSTRATION — EKF Multi-Target Tracker")
    print("=" * 72)

    scan_period = tws.scan_controller.scan_period
    print(f"\nScan volume: 120 deg  |  Scan rate: {engine.radar.scan_rate} deg/s")
    print(f"Scan period: {scan_period:.1f} s  |  Beamwidth: {engine.radar.beamwidth_az} deg")
    print(f"Simulation: 25 s at 50 ms steps\n")

    dt = 0.05
    total_time = 25.0
    steps = int(total_time / dt)
    last_reported_scan = -1

    # Ground truth target IDs
    gt_ids = {t.id for t in engine.scenario.targets}

    for step in range(steps):
        frame = engine.tick(dt=dt)

        # Report every full scan period
        current_scan = tws.scan_controller.completed_scans // 2  # full L-R-L cycles
        if current_scan > last_reported_scan and current_scan > 0:
            last_reported_scan = current_scan
            t = frame.time

            all_tracks = tws.track_manager.get_active_tracks()
            confirmed = tws.track_manager.get_confirmed_tracks()
            tentative = [tk for tk in all_tracks if tk.status == TrackStatus.TENTATIVE]

            print(f"--- Scan cycle {current_scan} (t = {t:.1f} s) ---")
            print(f"  Active tracks: {len(all_tracks)}  "
                  f"(confirmed: {len(confirmed)}, tentative: {len(tentative)})")

            if confirmed:
                print(f"  {'Track':>6s} | {'Status':>10s} | {'Hits':>4s} | "
                      f"{'Range':>9s} | {'Pos Unc':>9s} | {'Vel (vx,vy)':>18s}")
                print(f"  {'-'*6} | {'-'*10} | {'-'*4} | "
                      f"{'-'*9} | {'-'*9} | {'-'*18}")
                for tk in confirmed:
                    x, y = tk.ekf.position
                    vx, vy = tk.ekf.velocity
                    r = np.sqrt(x**2 + y**2)
                    unc = tk.ekf.position_uncertainty
                    print(f"  {tk.track_id:>6s} | {tk.status.value:>10s} | "
                          f"{tk.hits:>4d} | {r/1000:7.1f} km | "
                          f"{unc/1000:7.2f} km | "
                          f"({vx:+7.0f}, {vy:+7.0f}) m/s")
            print()

    # ── Final summary ────────────────────────────────────────────────
    print("=" * 72)
    print("FINAL TRACK SUMMARY")
    print("=" * 72)

    confirmed = tws.track_manager.get_confirmed_tracks()
    print(f"\nConfirmed tracks: {len(confirmed)}")

    # Show position error vs ground truth
    gt_targets = {t["id"]: t for t in frame.targets}
    print(f"\n  {'Track':>6s} | {'Hits':>4s} | {'Est Range':>10s} | "
          f"{'Est Vel':>18s} | {'Pos Unc':>9s}")
    print(f"  {'-'*6} | {'-'*4} | {'-'*10} | {'-'*18} | {'-'*9}")
    for tk in confirmed:
        x, y = tk.ekf.position
        vx, vy = tk.ekf.velocity
        r = np.sqrt(x**2 + y**2)
        unc = tk.ekf.position_uncertainty
        print(f"  {tk.track_id:>6s} | {tk.hits:>4d} | {r/1000:8.1f} km | "
              f"({vx:+7.0f}, {vy:+7.0f}) m/s | {unc/1000:7.2f} km")

    # ── Compare with snapshot modes ──────────────────────────────────
    print(f"\n{'=' * 72}")
    print("COMPARISON: Single-snapshot modes vs TWS tracks")
    print(f"{'=' * 72}")

    for mode_enum in [RadarMode.SRC, RadarMode.MTI, RadarMode.PULSE_DOPPLER]:
        np.random.seed(42)
        snap_engine = SimulationEngine(clutter=ClutterParams(enabled=False))
        snap_engine.set_mode(mode_enum)
        snap_frame = snap_engine.tick(dt=0.0)
        tgt_dets = {d.target_id for d in snap_frame.detections if d.target_id}
        print(f"  {snap_frame.mode:<30s}: {len(tgt_dets)} targets detected (snapshot)")

    print(f"  {'TWS (25s tracking)':<30s}: {len(confirmed)} confirmed tracks (persistent)")


if __name__ == "__main__":
    main()
