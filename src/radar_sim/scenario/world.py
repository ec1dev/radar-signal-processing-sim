"""
Scenario: manages the world state — targets, their motion, time progression.
"""

import numpy as np
from radar_sim.models import Target


class Scenario:
    """
    The ground-truth world. Targets move, time advances.
    The scenario knows nothing about radar — it's pure kinematics.
    """

    def __init__(self):
        self.targets: list[Target] = []
        self.time: float = 0.0

    def add_target(self, target: Target):
        self.targets.append(target)

    def update(self, dt: float):
        """Advance all targets by dt seconds."""
        for t in self.targets:
            t.update(dt)
        self.time += dt

    def reset(self):
        """Reset time to zero (does not reset target positions)."""
        self.time = 0.0

    @staticmethod
    def create_default_scenario() -> "Scenario":
        """
        A useful default: several targets at various ranges, speeds, and headings.
        Radar is assumed at origin facing north.
        """
        scenario = Scenario()

        # Target 1: Fighter, 40 km out, heading south (closing) at 250 m/s
        scenario.add_target(Target(
            id="tgt_1", x=5000, y=40000, altitude=6000,
            vx=0, vy=-250, rcs=3.0, label="fighter"
        ))

        # Target 2: Bomber, 80 km out, crossing left to right at 150 m/s
        scenario.add_target(Target(
            id="tgt_2", x=-10000, y=80000, altitude=8000,
            vx=150, vy=0, rcs=25.0, label="bomber"
        ))

        # Target 3: Cruise missile, 20 km, closing fast at 300 m/s, low RCS
        scenario.add_target(Target(
            id="tgt_3", x=1000, y=20000, altitude=100,
            vx=0, vy=-300, rcs=0.1, label="cruise_missile"
        ))

        # Target 4: Helicopter, 15 km, slow mover — near MTI blind speed territory
        scenario.add_target(Target(
            id="tgt_4", x=-3000, y=15000, altitude=500,
            vx=20, vy=-10, rcs=10.0, label="helicopter"
        ))

        # Target 5: Fighter at ~30 km, moving at EXACTLY the first blind speed
        # This is the MTI demo target — it will vanish when you switch to MTI
        scenario.add_target(Target(
            id="tgt_5", x=0, y=30000, altitude=6000,
            vx=0, vy=-29.98, rcs=5.0, label="fighter_blind"
            # vy=-29.98 ≈ first blind speed (λ*PRF/2 = 0.03*2000/2 = 30 m/s)
        ))

        return scenario
