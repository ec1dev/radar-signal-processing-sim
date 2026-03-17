# Radar Physics Model

This document describes the physical models underlying the simulation.

## Radar Range Equation

The received power from a target is given by the monostatic radar equation:

$$P_r = \frac{P_t \cdot G^2 \cdot \lambda^2 \cdot \sigma}{(4\pi)^3 \cdot R^4}$$

| Parameter | Symbol | Default Value |
|-----------|--------|---------------|
| Peak transmit power | $P_t$ | 50 kW |
| Antenna gain | $G$ | 33 dBi (1995 linear) |
| Wavelength | $\lambda$ | 0.03 m (X-band, 10 GHz) |
| Target RCS | $\sigma$ | varies per target |
| Range | $R$ | varies |

### Worked Example: Fighter at 40 km

For `tgt_1` (fighter, RCS = 3 m², range = 40 km):

```
Numerator  = 50000 × 1995² × 0.03² × 3.0
           = 50000 × 3.98e6 × 9e-4 × 3.0
           = 5.37e8

Denominator = (4π)³ × (40000)⁴
            = 1984 × 2.56e18
            = 5.08e21

Pr = 5.37e8 / 5.08e21 = 1.06e-13 W
```

This is about 10 dB above the noise floor — detectable but marginal in a single pulse.

## Doppler Effect

A target with radial velocity $v_r$ (positive = closing) produces a Doppler shift:

$$f_d = \frac{2 v_r}{\lambda}$$

**Example:** A fighter closing at 250 m/s at X-band:

$$f_d = \frac{2 \times 250}{0.03} = 16{,}667 \text{ Hz}$$

The sign convention: positive $v_r$ means the target is closing (moving toward the radar), which produces a positive Doppler shift.

## Thermal Noise Model

The receiver noise power is:

$$P_n = k T B F$$

| Parameter | Symbol | Value |
|-----------|--------|-------|
| Boltzmann constant | $k$ | 1.381 × 10⁻²³ J/K |
| System temperature | $T$ | 290 K |
| Receiver bandwidth | $B$ | 1 MHz |
| Noise figure | $F$ | 4 dB (2.51 linear) |

$$P_n = 1.381 \times 10^{-23} \times 290 \times 10^6 \times 2.51 = 1.01 \times 10^{-14} \text{ W}$$

## Signal-to-Noise Ratio

$$\text{SNR} = \frac{P_r}{P_n} \quad \text{(dB: } 10 \log_{10}(P_r / P_n)\text{)}$$

Detection requires SNR exceeding a threshold (default: 13 dB, corresponding to a detection probability of ~0.9 with a false alarm rate of ~10⁻⁶ for a Swerling I target).

## Clutter Model

Ground clutter is modelled as distributed scatterers across range cells. Each cell has an effective RCS:

$$\sigma_{\text{clutter}} = \sigma_0 \cdot A_{\text{cell}}$$

where:
- $\sigma_0$ is the terrain reflectivity (default: -20 dB/m²)
- $A_{\text{cell}} = \Delta R \cdot R \cdot \theta_{az}$ is the illuminated cell area
- $\Delta R$ is the range resolution (150 m)
- $\theta_{az}$ is the azimuth beamwidth (3° = 0.052 rad)

**Key insight:** Clutter power scales as $R^{-3}$, not $R^{-4}$ like targets, because the cell area grows linearly with range. This means clutter dominates at close range and falls off more slowly than targets.

Each clutter cell is assigned near-zero radial velocity with a small Gaussian spread (σ = 0.5 m/s) to model wind-induced clutter motion.

## Range and Velocity Ambiguity

With a pulsed radar, both range and Doppler are sampled discretely:

| Parameter | Formula | Default Value |
|-----------|---------|---------------|
| Max unambiguous range | $R_{\text{unamb}} = c / (2 \cdot \text{PRF})$ | 74,948 m |
| Max unambiguous velocity | $v_{\text{unamb}} = \lambda \cdot \text{PRF} / 4$ | 15 m/s |
| Range resolution | $\Delta R = c \cdot \tau / 2$ | 150 m |

The **PRF dilemma**: high PRF gives large unambiguous velocity but short unambiguous range, and vice versa. This is why Pulse Doppler radars must deal with range ambiguity — they use high PRF for velocity resolution at the cost of range folding.

Targets beyond $R_{\text{unamb}}$ appear at a folded range:

$$R_{\text{apparent}} = R_{\text{true}} \bmod R_{\text{unamb}}$$
