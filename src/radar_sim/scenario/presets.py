"""
Named scenario presets with real-world flavor.

Each factory method creates a Scenario with targets chosen to demonstrate
specific radar engineering concepts.
"""

from radar_sim.models import Target, ClutterParams
from radar_sim.scenario.world import Scenario


def create_bvr_engagement() -> Scenario:
    """Two fighters closing head-on at high speed with a jammed escort.

    Tests long-range detection, PD velocity resolution, and the effect
    of reduced RCS (jamming modeled as RCS * 0.01).
    """
    s = Scenario()
    s.add_target(Target(
        id="blue_1", x=0, y=50000, altitude=9000,
        vx=0, vy=-400, rcs=3.0, label="fighter",
    ))
    s.add_target(Target(
        id="red_1", x=0, y=100000, altitude=9000,
        vx=0, vy=-350, rcs=5.0, label="fighter",
    ))
    s.add_target(Target(
        id="red_2_jammed", x=5000, y=95000, altitude=9000,
        vx=0, vy=-350, rcs=0.05, label="fighter_jammed",
    ))
    return s


def create_low_altitude_intercept() -> Scenario:
    """Cruise missile and helicopter in heavy ground clutter.

    Tests clutter rejection and small-RCS detection at low altitude.
    Use with ClutterParams(reflectivity_db=-15) for heavy clutter.
    """
    s = Scenario()
    s.add_target(Target(
        id="cm_1", x=500, y=25000, altitude=50,
        vx=0, vy=-280, rcs=0.05, label="cruise_missile",
    ))
    s.add_target(Target(
        id="helo_1", x=-2000, y=12000, altitude=200,
        vx=15, vy=-5, rcs=15.0, label="helicopter",
    ))
    return s


def create_blind_speed_demo() -> Scenario:
    """Five targets at fractions of the first MTI blind speed.

    With default params: blind speed = lambda * PRF / 2 = 30 m/s.
    Targets at 0.25x, 0.5x, 0.75x, 1.0x, 1.25x the blind speed.
    """
    s = Scenario()
    blind = 30.0  # m/s for default params
    for i, frac in enumerate([0.25, 0.50, 0.75, 1.00, 1.25]):
        s.add_target(Target(
            id=f"bs_{frac:.2f}", x=0, y=30000, altitude=6000,
            vx=0, vy=-(frac * blind), rcs=5.0,
            label=f"{frac:.0%}_blind",
        ))
    return s


def create_range_ambiguity_demo() -> Scenario:
    """Targets at multiples of the max unambiguous range.

    With default PRF=2000: R_unamb = 74,948 m.
    Targets at 0.5x, 0.8x, 1.1x, 1.5x, 2.0x.
    """
    r_unamb = 74948.0
    s = Scenario()
    for m in [0.5, 0.8, 1.1, 1.5, 2.0]:
        s.add_target(Target(
            id=f"ra_{m:.1f}x", x=0, y=m * r_unamb, altitude=5000,
            vx=0, vy=-100, rcs=10.0,
            label=f"{m:.1f}x_Runamb",
        ))
    return s


def create_dense_environment() -> Scenario:
    """Twelve targets at various ranges, speeds, and RCS values.

    Mix of fighters, bombers, cruise missiles, helicopters, UAVs.
    Tests TWS track management under load.
    """
    s = Scenario()
    targets = [
        ("ftr_1", 5000, 40000, 8000, 0, -300, 3.0, "fighter"),
        ("ftr_2", -8000, 35000, 7000, 50, -250, 3.0, "fighter"),
        ("ftr_3", 12000, 55000, 9000, -30, -200, 1.2, "fighter"),
        ("bmb_1", -5000, 70000, 10000, 100, -50, 25.0, "bomber"),
        ("cm_1", 1000, 20000, 100, 0, -280, 0.1, "cruise_missile"),
        ("cm_2", -3000, 28000, 80, 10, -290, 0.1, "cruise_missile"),
        ("helo_1", -4000, 12000, 500, 20, -10, 10.0, "helicopter"),
        ("helo_2", 6000, 18000, 300, -15, -5, 12.0, "helicopter"),
        ("uav_1", 2000, 45000, 5000, 0, -60, 0.5, "uav"),
        ("uav_2", -1000, 30000, 4000, 10, -40, 0.01, "stealth_uav"),
        ("tpt_1", 0, 60000, 11000, 80, 0, 40.0, "transport"),
        ("awacs", -15000, 90000, 12000, 50, -20, 50.0, "awacs"),
    ]
    for tid, x, y, alt, vx, vy, rcs, label in targets:
        s.add_target(Target(
            id=tid, x=x, y=y, altitude=alt,
            vx=vx, vy=vy, rcs=rcs, label=label,
        ))
    return s
