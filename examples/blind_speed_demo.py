"""
MTI blind speed demonstration.

Creates targets at various fractions of the first blind speed and shows
how the MTI filter response determines detection/miss.  Also runs Pulse
Doppler on the same scenario to show its advantages and limitations.

Usage:
    python -m examples.blind_speed_demo
"""

import numpy as np

from radar_sim.models import RadarParams, Target, RadarMode, ClutterParams
from radar_sim.engine import SimulationEngine
from radar_sim.scenario.world import Scenario
from radar_sim.modes.mti import MTIMode


def main() -> None:
    np.random.seed(42)
    radar = RadarParams()
    blind_speed = radar.wavelength * radar.prf / 2  # 30 m/s

    print("=" * 72)
    print("MTI BLIND SPEED DEMONSTRATION")
    print("=" * 72)
    print(f"\nRadar: {radar.frequency/1e9:.0f} GHz  PRF={radar.prf:.0f} Hz  "
          f"\u03bb={radar.wavelength*100:.1f} cm")
    print(f"First blind speed: v_blind = \u03bb\u00b7PRF/2 = {blind_speed:.1f} m/s")

    # ── Build scenario with targets at fractions of blind speed ──────
    fractions = [0.25, 0.50, 0.75, 1.00, 1.25]
    scenario = Scenario()
    for i, frac in enumerate(fractions):
        v = frac * blind_speed
        scenario.add_target(Target(
            id=f"v_{frac:.2f}", x=0, y=30000, altitude=6000,
            vx=0, vy=-v, rcs=5.0,
            label=f"{frac:.0%} blind",
        ))

    # ── MTI filter response ──────────────────────────────────────────
    mti = MTIMode(radar, num_pulses=2)
    print(f"\nMTI filter response: |H(f)|^2 = sin^2(\u03c0\u00b7f_d/PRF)")
    print(f"\n  {'ID':>8s} | {'Velocity':>10s} | {'Doppler':>10s} | "
          f"{'MTI Gain':>10s} | {'Status'}")
    print(f"  {'-'*8} | {'-'*10} | {'-'*10} | {'-'*10} | {'-'*12}")

    for t in scenario.targets:
        v_r = abs(t.vy)
        f_d = 2 * v_r / radar.wavelength
        gain = mti.mti_filter_response(f_d)
        status = "DETECTED" if gain > 0.05 else "BLIND"
        print(f"  {t.id:>8s} | {v_r:8.1f} m/s | {f_d:8.1f} Hz | "
              f"{gain:10.4f} | {status}")

    # ── Run MTI mode ─────────────────────────────────────────────────
    engine = SimulationEngine(
        scenario=scenario, clutter=ClutterParams(enabled=False),
    )
    engine.set_mode(RadarMode.MTI)
    frame = engine.tick(dt=0.0)
    mti_ids = {d.target_id for d in frame.detections if d.target_id}

    print(f"\nMTI detected: {sorted(mti_ids) if mti_ids else 'none'}")

    # ── Run PD mode ──────────────────────────────────────────────────
    np.random.seed(42)
    engine2 = SimulationEngine(
        scenario=scenario, clutter=ClutterParams(enabled=False),
    )
    engine2.set_mode(RadarMode.PULSE_DOPPLER)
    pd_frame = engine2.tick(dt=0.0)
    pd_ids = {d.target_id for d in pd_frame.detections if d.target_id}

    print(f"PD detected:  {sorted(pd_ids) if pd_ids else 'none'}")
    print(f"\nNote: v=1.00\u00d7blind_speed has Doppler = PRF, which aliases to 0 Hz")
    print(f"      and falls in PD's clutter notch.  PRF agility would resolve this.")


if __name__ == "__main__":
    main()
