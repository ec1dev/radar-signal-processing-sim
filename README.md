# Radar Signal Processing Simulator

An interactive, real-time radar simulation demonstrating how different signal processing modes handle airborne target detection in clutter. Features signal-level Pulse Doppler processing with FFT-based range-Doppler mapping, Extended Kalman Filter tracking, and a live B-scope web display.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![Tests](https://img.shields.io/badge/tests-105%20passing-green)
![License](https://img.shields.io/badge/license-MIT-green)

## Demo

| SRC (Search) | MTI (Moving Target Indication) |
| :---: | :---: |
| *Sea of clutter with targets buried in noise* | *Clutter eliminated -- targets at blind speeds vanish* |

| Pulse Doppler | TWS (Track-While-Scan) |
| :---: | :---: |
| *Clean detections with calibrated velocity* | *EKF tracks building over multiple scan cycles* |

> Run `python -m radar_sim` + `cd frontend && npm run dev` to see the full interactive B-scope display.

## Why This Project Exists

Radar signal processing is foundational to defense and aerospace systems, but the tradeoffs between processing modes are hard to understand without seeing them side by side. This simulator lets you toggle between four modes on the same airborne scenario and immediately see the consequences: clutter flooding the display in SRC, blind speed targets vanishing in MTI, range ambiguities folding in Pulse Doppler, and tracks converging in TWS.

Growing up watching radar displays in DCS World and War Thunder, I wanted to understand the real engineering behind what those games simulate. This project is the result -- the same signal processing concepts that drive the AN/APG-68 and AN/AWG-9, implemented with real math and real physics, not game-engine approximations.

Every mode uses actual radar engineering: the radar range equation for power computation, Doppler shift for velocity, Kaiser-windowed FFT for spectral analysis, CFAR for adaptive detection, and an Extended Kalman Filter for target tracking. The web frontend renders a B-scope display modeled after real fighter radar displays.

## Architecture

```text
Scenario Engine          Signal Processing Modes            Frontend
+--------------+        +------------------------+       +--------------+
|  Targets     |        |  SRC   (range gating)  |       |  B-Scope     |
|  Motion      |--raw-->|  MTI   (3-pulse cancel) |--det->|  Display     |
|  Clutter     | returns|  PD    (FFT / CFAR)    |       |  Controls    |
|  Noise       |        |  TWS   (EKF tracking)  |       |  Parameters  |
+--------------+        +------------------------+       +--------------+
      ^                          ^                            ^
      |                          |                            |
  Radar Equation            Plugin Architecture          WebSocket
  R^4 propagation           BaseMode interface           Real-time
  Doppler shift             Independent processing       20 Hz updates
```

## Mode Comparison

Results from the default scenario (5 airborne targets + 200 ground clutter cells):

| Metric | SRC | MTI | Pulse Doppler | TWS |
| -------- | ----- | ----- | --------------- | ----- |
| Targets detected (of 5) | 3 | 1 | 4 | 4 (tracked) |
| Clutter false alarms | 197 | 10 | 5 | 0 |
| Velocity measurement | No | Approximate | Precise (FFT) | Filtered (EKF) |
| Clutter rejection | None | 3-pulse cancellation | Doppler notch + CFAR | Via detection mode |
| Tracking | No | No | No | Extended Kalman Filter |
| Key weakness | Drowns in clutter | Blind speeds | Range ambiguity | Slow update rate |

## Key Demonstrations

**MTI blind speed.** Target `tgt_5` moves at exactly 30 m/s -- the first blind speed (`v = lambda * PRF / 2`). Its Doppler phase shift between pulses is exactly `2*pi`, making it indistinguishable from clutter. MTI cancels it completely.

**Clutter rejection.** SRC produces 197 clutter false alarms. MTI eliminates nearly all of them through pulse cancellation. Pulse Doppler reduces clutter to 5 through spectral notching and CFAR adaptive thresholding.

**Range ambiguity.** The bomber (`tgt_2`) at 80 km is beyond the max unambiguous range of 74.9 km. Pulse Doppler detects it at the folded range of 5.8 km and flags it as ambiguous.

**Low-RCS detection.** The cruise missile (`tgt_3`, RCS = 0.1 m^2) is buried in clutter for SRC but resolves cleanly in Pulse Doppler because its high closing velocity places it in a distinct Doppler bin away from the clutter notch.

**EKF convergence.** TWS builds confirmed tracks over multiple antenna scan cycles. Position uncertainty decreases from ~750 m to ~450 m as the EKF accumulates measurements, and velocity estimates converge to within a few m/s of ground truth.

## Default Scenario

Each target was chosen to demonstrate a specific radar engineering concept:

| Target | Type | Range | Speed | RCS | Purpose |
| -------- | -------- | ------- | ------- | ------- | --------- |
| tgt_1 | Fighter | 40 km | 250 m/s | 3 m^2 | Medium target at moderate range |
| tgt_2 | Bomber | 80 km | 150 m/s | 25 m^2 | Beyond R_unamb -- tests PD range folding |
| tgt_3 | Cruise missile | 20 km | 300 m/s | 0.1 m^2 | Low RCS -- tests sensitivity in clutter |
| tgt_4 | Helicopter | 15 km | 22 m/s | 10 m^2 | Slow mover, strong return |
| tgt_5 | Fighter | 30 km | 30 m/s | 5 m^2 | Exactly at first MTI blind speed |

## Signal Processing Detail

### Pulse Doppler

CPI waveform synthesis (64 pulses) -- Kaiser window (beta=14, -80 dB sidelobes) -- N-point FFT -- range-Doppler map -- clutter notch (+-5 bins around DC) -- CA-CFAR with guard/training cells -- 2D peak detection to collapse spectral leakage.

### MTI

3-pulse canceller with frequency response `|H(f)|^2 = sin^4(pi * f_d / PRF)`. Zero at DC (clutter cancelled) and at blind speeds `v = n * lambda * PRF / 2`. First blind speed = 30 m/s with default parameters.

### TWS

Extended Kalman Filter with 4-state constant-velocity model `[x, vx, y, vy]`. Measurements in polar (range, azimuth) with nonlinear measurement function and Jacobian. Mahalanobis gating for detection-to-track association. M-of-N (3/5) confirmation rule. Antenna scans 120 deg at 60 deg/s.

See [docs/physics.md](docs/physics.md), [docs/modes.md](docs/modes.md), and [docs/architecture.md](docs/architecture.md) for full mathematical treatment.

## Quick Start

```bash
# Clone and install
git clone https://github.com/ec1dev/radar-signal-processing-sim.git
cd radar-signal-processing-sim
pip install -e ".[dev]"

# Run the mode comparison
python -m examples.basic_comparison

# Run the interactive demo
python -m radar_sim                           # Terminal 1: backend
cd frontend && npm install && npm run dev     # Terminal 2: frontend
# Open http://localhost:5173

# Run tests
pytest
```

### Example Scripts

```bash
python -m examples.basic_comparison      # SRC vs MTI vs PD comparison table
python -m examples.blind_speed_demo      # MTI blind speed analysis
python -m examples.range_ambiguity_demo  # PD range folding demonstration
python -m examples.clutter_rejection     # Clutter false alarm comparison
python -m examples.tws_tracking_demo     # TWS multi-target tracking
python -m examples.rcs_comparison        # Detection range vs RCS (stealth analysis)
python -m examples.platform_comparison   # Fighter vs AWACS vs ground radar
```

## Project Structure

```text
src/radar_sim/
├── models.py                  # Core data types and radar parameters
├── engine.py                  # Simulation controller
├── radar/
│   └── physics.py             # Radar equation, Doppler, clutter model
├── modes/
│   ├── base_mode.py           # Plugin interface (BaseMode ABC)
│   ├── src.py                 # Search (range-gated threshold)
│   ├── mti.py                 # Moving Target Indication (3-pulse canceller)
│   ├── pulse_doppler.py       # Signal-level PD (FFT, CFAR, peak detection)
│   └── tws/                   # Track-While-Scan
│       ├── ekf_tracker.py         # Extended Kalman Filter
│       ├── track_manager.py       # Track lifecycle (M-of-N confirmation)
│       ├── scan_controller.py     # Antenna raster scan model
│       └── association.py         # Mahalanobis gating + nearest-neighbour
├── scenario/
│   ├── world.py               # Scenario engine and defaults
│   ├── presets.py             # Named scenarios (BVR, low-alt, dense)
│   └── rcs_database.py       # Aircraft RCS reference data
└── api/
    └── server.py              # FastAPI WebSocket server (20 Hz)
frontend/                      # React + TypeScript B-scope display
tests/                         # 105 tests
examples/                      # Runnable demonstrations
docs/                          # Technical documentation
```

## Roadmap

- [x] SRC search mode
- [x] MTI with blind speed modeling (3-pulse canceller)
- [x] Signal-level Pulse Doppler (FFT, CFAR, peak detection)
- [x] TWS with Extended Kalman Filter and multi-target tracking
- [x] Interactive web frontend (B-scope display)
- [x] Real-time parameter adjustment (PRF, power, threshold)
- [x] Named scenario presets with real-world flavor
- [ ] Probabilistic detection model (Pd/Pfa with Swerling cases)
- [ ] PRF agility (multiple PRFs for blind speed / range ambiguity resolution)
- [ ] Aspect-dependent RCS models
- [ ] ECCM techniques (sidelobe blanking, frequency agility)
- [ ] Single Target Track (STT) mode
- [ ] Terrain-aware clutter model (DEM-based)
- [ ] Multi-radar fusion

## References

- Skolnik, M. -- *Introduction to Radar Systems* (3rd ed.)
- Richards, M. -- *Fundamentals of Radar Signal Processing* (2nd ed.)
- Stimson, G.W. -- *Introduction to Airborne Radar* (2nd ed.)
- Barton, D.K. -- *Radar System Analysis and Modeling*

## License

MIT
