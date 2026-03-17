"""
Main simulation engine.
Ties together the scenario, physics, and active mode.
Runs the simulation loop and produces detection frames.
"""

from dataclasses import dataclass
from radar_sim.models import RadarParams, RadarPosition, ClutterParams, Detection, RadarMode
from radar_sim.scenario.world import Scenario
from radar_sim.radar.physics import PhysicsEngine
from radar_sim.modes.base_mode import BaseMode
from radar_sim.modes.src import SRCMode
from radar_sim.modes.mti import MTIMode
from radar_sim.modes.pulse_doppler import PulseDopplerMode
from radar_sim.modes.tws import TWSMode


@dataclass
class SimulationFrame:
    """One frame of simulation output — what gets sent to the frontend."""
    time: float
    mode: str
    detections: list[Detection]
    # Ground truth (for debug overlay / educational display)
    targets: list[dict]   # [{id, x, y, range, velocity, rcs}, ...]
    radar_params_summary: dict


class SimulationEngine:
    """
    The main simulation controller.

    Usage:
        engine = SimulationEngine()
        engine.set_mode(RadarMode.SRC)
        frame = engine.tick(dt=0.05)  # 20 Hz update
    """

    def __init__(
        self,
        scenario: Scenario | None = None,
        radar: RadarParams | None = None,
        position: RadarPosition | None = None,
        clutter: ClutterParams | None = None,
    ):
        self.scenario = scenario or Scenario.create_default_scenario()
        self.radar = radar or RadarParams()
        self.position = position or RadarPosition()
        self.clutter = clutter or ClutterParams()

        self.physics = PhysicsEngine(self.radar, self.position, self.clutter)

        # Initialize available modes
        self._modes: dict[RadarMode, BaseMode] = {
            RadarMode.SRC: SRCMode(self.radar),
            RadarMode.MTI: MTIMode(self.radar, num_pulses=2),
            RadarMode.PULSE_DOPPLER: PulseDopplerMode(self.radar),
            RadarMode.TWS: TWSMode(self.radar, position=self.position),
        }

        self._active_mode: RadarMode = RadarMode.SRC

    @property
    def active_mode(self) -> BaseMode:
        return self._modes[self._active_mode]

    def set_mode(self, mode: RadarMode):
        """Switch the active radar mode."""
        if mode not in self._modes:
            raise ValueError(f"Mode {mode} not yet implemented")
        self._active_mode = mode

    def update_radar_param(self, param: str, value: float):
        """Update a radar parameter dynamically (e.g., PRF, power)."""
        if hasattr(self.radar, param):
            setattr(self.radar, param, value)
            # Rebuild physics engine with updated params
            self.physics = PhysicsEngine(self.radar, self.position, self.clutter)
            # Rebuild modes with updated params
            for mode_enum, mode_obj in self._modes.items():
                self._modes[mode_enum] = type(mode_obj)(self.radar)
        else:
            raise ValueError(f"Unknown radar parameter: {param}")

    def tick(self, dt: float = 0.05) -> SimulationFrame:
        """
        Advance the simulation by dt seconds and produce one output frame.

        Steps:
        1. Update target positions
        2. Compute raw returns (physics)
        3. Process through active mode
        4. Package as a frame for the frontend
        """
        # 1. Update world
        self.scenario.update(dt)

        # 2. Compute raw returns
        raw_returns = self.physics.compute_all_returns(self.scenario.targets)

        # 3. Advance stateful modes (TWS needs scan + prediction step)
        if hasattr(self.active_mode, 'tick'):
            self.active_mode.tick(dt)

        # 4. Process through active mode
        detections = self.active_mode.process(raw_returns)

        # 5. Build ground truth for debug overlay
        target_truth = []
        for t in self.scenario.targets:
            dx = t.x - self.position.x
            dy = t.y - self.position.y
            dz = t.altitude - self.position.altitude
            r = (dx**2 + dy**2 + dz**2) ** 0.5
            ux, uy = dx / max(r, 1), dy / max(r, 1)
            v_r = -(t.vx * ux + t.vy * uy)

            target_truth.append({
                "id": t.id,
                "label": t.label,
                "x": t.x,
                "y": t.y,
                "altitude": t.altitude,
                "range_m": r,
                "radial_velocity": v_r,
                "speed": t.speed,
                "rcs": t.rcs,
            })

        # 6. Radar params summary
        params_summary = {
            "frequency_ghz": self.radar.frequency / 1e9,
            "prf_hz": self.radar.prf,
            "power_w": self.radar.power,
            "pulse_width_us": self.radar.pulse_width * 1e6,
            "max_unamb_range_km": self.radar.max_unambiguous_range / 1000,
            "max_unamb_velocity_mps": self.radar.max_unambiguous_velocity,
            "range_resolution_m": self.radar.range_resolution,
            "blind_speeds_mps": self.radar.blind_speeds,
        }

        return SimulationFrame(
            time=self.scenario.time,
            mode=self.active_mode.name,
            detections=detections,
            targets=target_truth,
            radar_params_summary=params_summary,
        )

