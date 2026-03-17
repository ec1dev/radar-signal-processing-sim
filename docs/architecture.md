# System Architecture

## Overview

The simulator is organized as a pipeline with clean separation between scenario definition, physics computation, and signal processing:

```
Scenario (targets, kinematics)
    |
    v
PhysicsEngine (radar equation, Doppler, clutter)
    |
    v
list[RawReturn]  --- received power, range, Doppler per scatterer
    |
    +---> SRCMode ----------> Range gating + threshold
    +---> MTIMode ----------> Pulse cancellation filter
    +---> PulseDopplerMode -> FFT + clutter notch + CFAR
              |
              v
       list[Detection]  --- range, velocity, SNR, ambiguity flags
```

Each stage is independent: you can swap scenarios without touching the physics, or add new modes without modifying the engine.

## Data Flow

### 1. Scenario Layer (`scenario/world.py`)

The `Scenario` class manages target kinematics. Each `Target` has position (x, y, altitude), velocity (vx, vy), RCS, and a label. The scenario advances time via `update(dt)`, which moves all targets according to their velocities.

The scenario knows nothing about radar — it is pure kinematics.

### 2. Physics Layer (`radar/physics.py`)

The `PhysicsEngine` takes the radar parameters, radar position, and clutter configuration. It computes:

- **Target returns:** For each target, compute slant range, radial velocity, Doppler shift, and received power via the radar range equation.
- **Clutter returns:** Generate distributed ground clutter across range cells with near-zero Doppler.

Output: `list[RawReturn]`, each containing `range_m`, `radial_velocity`, `received_power`, `doppler_hz`, and metadata.

### 3. Mode Layer (`modes/`)

Each mode implements `BaseMode.process(raw_returns) -> list[Detection]`. The mode applies its signal processing chain to the raw returns and produces detections with range, velocity (if available), SNR, and metadata.

### 4. Engine Layer (`engine.py`)

The `SimulationEngine` ties everything together. It holds the scenario, physics engine, and all registered modes. The `tick(dt)` method:

1. Advances the scenario
2. Computes raw returns
3. Processes through the active mode
4. Packages results as a `SimulationFrame`

## Package Structure

```
src/radar_sim/
├── __init__.py          # Package root, version
├── models.py            # All data types: Target, RadarParams, Detection, RawReturn, etc.
├── engine.py            # SimulationEngine: ties scenario + physics + modes
├── radar/
│   ├── __init__.py
│   └── physics.py       # PhysicsEngine: radar equation, Doppler, clutter
├── scenario/
│   ├── __init__.py
│   └── world.py         # Scenario: target management, kinematics
└── modes/
    ├── __init__.py
    ├── base_mode.py      # BaseMode ABC: interface all modes implement
    ├── src.py            # SRC: range-gated search
    ├── mti.py            # MTI: pulse cancellation
    └── pulse_doppler.py  # PD: FFT + CFAR (signal-level processing)
```

## How to Add a New Mode

1. Create `src/radar_sim/modes/your_mode.py`
2. Subclass `BaseMode`:

```python
from radar_sim.modes.base_mode import BaseMode
from radar_sim.models import RawReturn, Detection, RadarParams

class YourMode(BaseMode):
    def __init__(self, radar: RadarParams):
        super().__init__(radar)

    @property
    def name(self) -> str:
        return "Your Mode Name"

    @property
    def description(self) -> str:
        return "What this mode does."

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        # Your signal processing here
        return detections
```

3. Add the enum value to `RadarMode` in `models.py`
4. Register in `SimulationEngine.__init__()` in `engine.py`:
```python
RadarMode.YOUR_MODE: YourMode(self.radar),
```

## How to Create Custom Scenarios

```python
from radar_sim.models import Target
from radar_sim.scenario.world import Scenario

scenario = Scenario()
scenario.add_target(Target(
    id="custom_1",
    x=10000, y=50000, altitude=8000,
    vx=-50, vy=-200,
    rcs=5.0,
    label="custom_fighter",
))

# Use with the engine:
engine = SimulationEngine(scenario=scenario)
```

## Extension Points

- **API server:** Add a FastAPI WebSocket server that streams `SimulationFrame` objects to a frontend in real time.
- **Frontend:** Build a React app with PPI (Plan Position Indicator) or B-scope display showing detections.
- **TWS mode:** Track-While-Scan with Kalman filter state estimation.
- **PRF agility:** Run multiple CPIs at different PRFs and correlate to resolve range/velocity ambiguities.
- **Antenna patterns:** Model the antenna beam pattern and scan scheduling for more realistic detection geometry.
