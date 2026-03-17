# Radar Signal Processing Simulator

An interactive radar simulation demonstrating SRC, MTI, and Pulse Doppler signal processing modes -- built with real signal-level DSP, not toy math.

## Overview

This project simulates an X-band airborne fighter radar (10 GHz, 50 kW peak power, PRF = 2000 Hz) processing the same airborne scenario through three fundamentally different signal processing modes. The simulation implements the complete data pipeline from target kinematics through the radar range equation to mode-specific detection algorithms.

The technically significant piece is the **Pulse Doppler mode**, which performs actual signal-level processing: complex waveform synthesis across a 64-pulse coherent processing interval, Kaiser-windowed FFT to produce a range-Doppler map, spectral clutter notching, and Cell-Averaging CFAR detection. This is the same processing chain used in radars like the APG-68 (F-16) and APG-73 (F/A-18) -- implemented here with NumPy vectorized operations.

The default scenario includes five targets designed to demonstrate each mode's strengths and failure cases: a low-RCS cruise missile that SRC misses in clutter, a fighter at the first MTI blind speed, and a bomber beyond the unambiguous range that folds into Pulse Doppler's detection window.

## Architecture

```
Scenario (5 targets, constant-velocity kinematics)
    |
    v
PhysicsEngine
    |  - Radar range equation: Pr = Pt*G^2*lam^2*sigma / (4*pi)^3*R^4
    |  - Doppler shift: fd = 2*vr / lam
    |  - Ground clutter: 200 cells with terrain reflectivity model
    v
list[RawReturn]  ---- received power, range, Doppler per scatterer
    |
    +---> SRCMode ------------> Range gating + fixed threshold
    |                           (no filtering -- everything detected)
    |
    +---> MTIMode ------------> sin^2(pi*fd/PRF) filter response
    |                           (clutter cancelled, blind speeds appear)
    |
    +---> PulseDopplerMode ---> Slow-time signal synthesis
              |                  Kaiser window (beta=14, -80 dB sidelobes)
              |                  N-point FFT --> range-Doppler map
              |                  Clutter notch (+-5 bins around DC)
              |                  CA-CFAR adaptive detection
              v
       list[Detection]  ---- range, velocity, SNR, ambiguity flags
```

## Mode Comparison

Results from the default scenario (5 airborne targets + 200 ground clutter cells):

| Metric | SRC | MTI | Pulse Doppler |
| -------- | ----- | ----- | --------------- |
| Targets detected (of 5) | 3 | 1-2 | 4 |
| Clutter false alarms | 197 | 0 | 3-7 |
| Velocity measurement | No | Approximate | Precise (FFT) |
| Clutter rejection | None | Pulse cancellation | Notch filter + CFAR |
| Key weakness | Drowns in clutter | Blind speeds | Range ambiguity |

## Key Demonstrations

**MTI blind speed.** Target `tgt_5` moves at exactly 30 m/s -- the first blind speed ($v = \lambda \cdot \text{PRF} / 2 = 0.03 \times 2000 / 2$). Its Doppler phase shift between pulses is exactly $2\pi$, making it indistinguishable from clutter. MTI cancels it completely.

**Pulse Doppler clutter rejection.** SRC produces 197 clutter false alarms. Pulse Doppler reduces this to 3-7 through spectral notching (zeroing Doppler bins near DC) and CFAR adaptive thresholding that distinguishes target peaks from clutter sidelobes.

**Range ambiguity.** The bomber (`tgt_2`) at 80 km is beyond the unambiguous range of 74.9 km. Pulse Doppler detects it at the folded range of 5.8 km ($80.7 \bmod 74.9$) and flags it as ambiguous.

**Low-RCS detection.** The cruise missile (`tgt_3`, RCS = 0.1 m^2) is buried in clutter for SRC but resolves cleanly in Pulse Doppler because its Doppler shift (291 m/s closing) places it in a distinct spectral bin away from the clutter notch.

## Technical Detail

### Radar Range Equation

$$P_r = \frac{P_t \cdot G^2 \cdot \lambda^2 \cdot \sigma}{(4\pi)^3 \cdot R^4}$$

With defaults: $P_t$ = 50 kW, $G$ = 33 dBi, $\lambda$ = 3 cm, $P_n = kTBF$ = 1.01 x 10^-14 W.

### Mode Processing

- **SRC:** Groups returns into 150 m range bins, sums power, thresholds at SNR > 13 dB. No filtering.
- **MTI:** Applies $|H(f)|^2 = \sin^2(\pi f_d / \text{PRF})$ gain to each return. Zero at DC (clutter) and at blind speeds ($v = n \cdot 30$ m/s).
- **Pulse Doppler:** Synthesizes slow-time signal $s[n] = \sum_k A_k e^{j 2\pi f_{d,k} n/\text{PRF}} + w[n]$, applies Kaiser window + FFT, notches DC, runs CA-CFAR with guard/training cells adapted around the notch.

See [docs/physics.md](docs/physics.md), [docs/modes.md](docs/modes.md), and [docs/architecture.md](docs/architecture.md) for full details.

## Quick Start

```bash
git clone https://github.com/<your-username>/radar-signal-processing-sim.git
cd radar-signal-processing-sim
pip install -e ".[dev]"

# Run the three-way mode comparison
python -m examples.basic_comparison

# Run the test suite
pytest
```

### Example Scripts

```bash
python -m examples.basic_comparison      # SRC vs MTI vs PD side-by-side
python -m examples.blind_speed_demo      # MTI blind speed analysis
python -m examples.range_ambiguity_demo  # PD range folding demonstration
python -m examples.clutter_rejection     # Clutter false alarm comparison
```

## Project Structure

```text
radar-signal-processing-sim/
├── src/radar_sim/               # Main package
│   ├── models.py                # Data types: Target, RadarParams, Detection, RawReturn
│   ├── engine.py                # SimulationEngine: ties scenario + physics + modes
│   ├── radar/physics.py         # Radar equation, Doppler, clutter model
│   ├── scenario/world.py        # Scenario management, target kinematics
│   └── modes/
│       ├── base_mode.py         # BaseMode ABC (plugin interface)
│       ├── src.py               # Search mode (range gating)
│       ├── mti.py               # Moving Target Indication (pulse canceller)
│       └── pulse_doppler.py     # Pulse Doppler (FFT + CFAR)
├── tests/                       # 81 pytest tests
├── examples/                    # Runnable demonstration scripts
├── docs/                        # Technical documentation
│   ├── physics.md               # Radar equation, noise, clutter derivations
│   ├── modes.md                 # Detailed mode processing documentation
│   └── architecture.md          # System design and extension guide
└── pyproject.toml               # Project metadata and tool configuration
```

## Roadmap

- [ ] TWS (Track-While-Scan) mode with Kalman filter state estimation
- [ ] FastAPI WebSocket server for real-time simulation streaming
- [ ] React frontend with PPI/B-scope radar display
- [ ] PRF agility for resolving blind speeds and range ambiguities
- [ ] Antenna scan pattern and beam shape modeling
- [ ] CFAR variants (OS-CFAR, GO-CFAR) for different clutter environments
- [ ] DRFM jammer modeling and electronic countermeasures

## License

MIT
