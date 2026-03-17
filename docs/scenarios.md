# Creating Custom Scenarios

## Basics

A `Scenario` holds a list of `Target` objects and advances their positions each tick.

```python
from radar_sim.models import Target
from radar_sim.scenario.world import Scenario

scenario = Scenario()
scenario.add_target(Target(
    id="my_fighter",
    x=10000,       # 10 km east of radar
    y=50000,       # 50 km north
    altitude=8000, # 8 km altitude
    vx=-50,        # moving west at 50 m/s
    vy=-200,       # closing at 200 m/s
    rcs=3.0,       # 3 m^2 RCS
    label="fighter",
))
```

Pass it to the engine:

```python
from radar_sim.engine import SimulationEngine
engine = SimulationEngine(scenario=scenario)
```

## Using preset scenarios

```python
from radar_sim.scenario.presets import create_bvr_engagement
engine = SimulationEngine(scenario=create_bvr_engagement())
```

Available presets: `create_bvr_engagement()`, `create_low_altitude_intercept()`, `create_blind_speed_demo()`, `create_range_ambiguity_demo()`, `create_dense_environment()`.

## Adjusting radar parameters

Model different platforms by changing `RadarParams`:

```python
from radar_sim.models import RadarParams

# AWACS-class radar (long range, low PRF)
awacs = RadarParams(
    frequency=3.0e9,     # S-band
    power=1_000_000,     # 1 MW
    gain_db=40.0,
    prf=300,             # low PRF for long unambiguous range
)

engine = SimulationEngine(radar=awacs, scenario=scenario)
```

## RCS reference data

Use the built-in RCS database for realistic target cross-sections:

```python
from radar_sim.scenario.rcs_database import RCS_DATABASE

rcs = RCS_DATABASE["F-16"]      # 1.2 m^2
rcs = RCS_DATABASE["B-52"]      # 100.0 m^2
rcs = RCS_DATABASE["F-22"]      # 0.0001 m^2 (stealth)
```

## Clutter configuration

```python
from radar_sim.models import ClutterParams

# Heavy clutter (urban/wet terrain)
heavy = ClutterParams(reflectivity_db=-15)

# No clutter (clean scenario for testing)
clean = ClutterParams(enabled=False)

engine = SimulationEngine(clutter=heavy, scenario=scenario)
```
