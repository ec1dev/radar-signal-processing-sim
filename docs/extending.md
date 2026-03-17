# Adding a New Radar Mode

All processing modes implement the `BaseMode` interface. Adding a new mode takes four steps.

## Step 1: Create the mode file

Create `src/radar_sim/modes/your_mode.py`:

```python
import numpy as np
from radar_sim.models import RawReturn, Detection, RadarParams
from radar_sim.modes.base_mode import BaseMode


class YourMode(BaseMode):
    """One-line description of what this mode does."""

    def __init__(self, radar: RadarParams):
        super().__init__(radar)

    @property
    def name(self) -> str:
        return "Your Mode Name"

    @property
    def description(self) -> str:
        return "Short description for the frontend."

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        # Your signal processing logic here.
        # Input:  list of RawReturn (range, Doppler, power, azimuth per scatterer)
        # Output: list of Detection (range, azimuth, velocity, SNR, flags)
        detections = []
        # ...
        return detections
```

The `process()` method receives the same raw returns that every other mode gets. You decide how to filter, threshold, and report detections.

## Step 2: Register in the engine

In `src/radar_sim/engine.py`, import and add your mode:

```python
from radar_sim.modes.your_mode import YourMode

# In SimulationEngine.__init__:
self._modes[RadarMode.YOUR_MODE] = YourMode(self.radar)
```

Add the enum value in `models.py`:

```python
class RadarMode(Enum):
    # ...
    YOUR_MODE = "your_mode"
```

## Step 3: Add tests

Create `tests/test_your_mode.py` following the patterns in `test_src_mode.py` and `test_mti_mode.py`.

## Step 4: Stateful modes

If your mode maintains state across ticks (like TWS), add a `tick(dt)` method. The engine automatically calls it before `process()`:

```python
def tick(self, dt: float) -> None:
    """Advance internal state by dt seconds."""
    self._time += dt
    # Update internal state...
```

## Example: Simple STT (Single Target Track) stub

```python
class STTMode(BaseMode):
    """Single Target Track -- dedicates the beam to one target."""

    @property
    def name(self) -> str:
        return "STT (Single Target Track)"

    @property
    def description(self) -> str:
        return "Dedicated tracking of a single target with high update rate."

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        # Find the strongest non-clutter return
        best = max(
            (r for r in raw_returns if not r.is_clutter),
            key=lambda r: r.received_power,
            default=None,
        )
        if best is None:
            return []
        snr = best.received_power / self.radar.noise_power
        if snr < 10 ** (self.radar.detection_threshold_db / 10):
            return []
        return [Detection(
            range_m=best.range_m,
            azimuth_deg=best.azimuth_deg,
            velocity_mps=best.radial_velocity,
            snr_db=float(10 * np.log10(snr)),
            target_id=best.target_id,
        )]
```
