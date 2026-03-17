# Signal Processing Modes

Each mode implements the same interface (`BaseMode.process()`) but applies fundamentally different signal processing to the raw returns.

## SRC (Search)

**Purpose:** Baseline range-gated detection with no filtering.

**Processing pipeline:**
1. Group raw returns into range bins (bin width = range resolution = 150 m)
2. Sum received power per bin across all scatterers (targets + clutter)
3. Compare total bin power against noise floor × threshold
4. Any bin above threshold generates a detection

**Strengths:**
- Simple, no information discarded
- Detects everything above the noise floor

**Weaknesses:**
- Cannot distinguish targets from clutter
- No velocity measurement
- Close-range clutter produces hundreds of false alarms

**Real-world analogy:** Early fire-control radars, basic weather radar, range-only search modes on legacy systems.

---

## MTI (Moving Target Indication)

**Purpose:** Cancel stationary clutter by exploiting Doppler phase shifts between pulses.

**Processing pipeline:**
1. Group returns into range bins (same as SRC)
2. For each return, compute the MTI filter response based on its Doppler frequency
3. Apply the filter gain to the return's power: $P_{\text{filtered}} = P_r \cdot |H(f_d)|^2$
4. Sum filtered power per bin and threshold

**Filter response (2-pulse canceller):**

$$|H(f)|^2 = \sin^2\!\left(\frac{\pi f_d}{\text{PRF}}\right)$$

- **Zero at DC** ($f_d = 0$): stationary clutter cancelled
- **Zero at blind speeds** ($f_d = n \cdot \text{PRF}$): targets at $v = n \cdot \lambda \cdot \text{PRF} / 2$ vanish
- **Maximum at** $f_d = \text{PRF}/2$: targets at half the blind speed have full response

**Blind speeds:** $v_{\text{blind}} = n \cdot \lambda \cdot \text{PRF} / 2$

With the default parameters: first blind speed = 0.03 × 2000 / 2 = **30 m/s**. This is physically realistic for a medium-PRF X-band radar.

**3-pulse canceller:** Uses $|H|^2 = \sin^4(\pi f_d / \text{PRF})$, giving deeper nulls at DC (better clutter rejection) but wider blind speed notches.

**Strengths:**
- Excellent clutter rejection — eliminates nearly all stationary returns
- Simple hardware implementation (analog delay-line canceller)

**Weaknesses:**
- Periodic blind speeds where targets vanish
- No precise velocity measurement
- Cannot distinguish blind-speed targets from clutter

**Real-world systems:** MiG-23's Sapfir-23ML, most legacy fighter radars, ATC primary surveillance radars (ASR-9), ground-based air defense (P-18).

---

## Pulse Doppler (PD)

**Purpose:** Simultaneous range and velocity measurement with clutter rejection through spectral processing.

This is the most technically sophisticated mode. Unlike SRC and MTI which use abstract power models, PD performs signal-level processing: actual waveform synthesis, windowed FFT, and adaptive detection.

**Processing pipeline:**

1. **Range binning with folding:** Assign returns to range bins, folding for ambiguity ($R_{\text{apparent}} = R_{\text{true}} \bmod R_{\text{unamb}}$)

2. **Slow-time signal synthesis:** For each range bin, construct the complex baseband signal across $N$ pulses:
$$s[n] = \sum_k A_k \cdot e^{j 2\pi f_{d,k} n / \text{PRF}} + w[n]$$
where $A_k = \sqrt{P_{r,k}}$ is the voltage amplitude and $w[n] \sim \mathcal{CN}(0, P_n)$

3. **Windowing:** Apply a Kaiser window ($\beta = 14$) to suppress spectral sidelobes to ~-80 dB. This is critical because close-range clutter can be 80+ dB above the noise floor, and without adequate sidelobe suppression, clutter energy leaks across the entire Doppler spectrum.

4. **FFT:** Transform along the pulse dimension to obtain the Doppler spectrum per range bin. Result: a range-Doppler map of size $(N_{\text{range}} \times N_{\text{pulses}})$.

5. **Clutter notch:** Zero out $\pm 5$ Doppler bins around DC. This eliminates the main clutter peak without the periodic blind speeds of MTI.

6. **CA-CFAR detection:** Cell-Averaging Constant False Alarm Rate detector along the Doppler dimension. For each cell, the noise floor is estimated from surrounding training cells (excluding guard cells and the notch region). Detection threshold adapts to local spectral conditions.

7. **Output:** Convert detected $(i_{\text{range}}, i_{\text{Doppler}})$ cells to $(R, v)$ using:
$$v = f_d \cdot \lambda / 2$$

**Key parameters:**

| Parameter | Default | Effect |
|-----------|---------|--------|
| N_pulses (CPI length) | 64 | More = finer velocity resolution, slower update |
| Notch half-width | 5 bins | Wider = more clutter rejection, larger velocity blind zone |
| CFAR guard cells | 6 | Must exceed notch width to avoid edge effects |
| CFAR training cells | 12 | More = better noise estimate, larger window |

**Velocity resolution:** $\Delta v = \lambda \cdot \text{PRF} / (2N) = 0.03 \times 2000 / 128 = 0.47$ m/s

**Strengths:**
- Velocity measurement on every detection
- No periodic blind speeds (narrow notch vs sinusoidal response)
- Coherent integration gain (~16 dB with 64 pulses)
- CFAR adapts to local clutter environment

**Weaknesses:**
- Range ambiguity with high PRF (targets beyond $R_{\text{unamb}}$ fold)
- Target at exactly the blind speed aliases to DC (in the notch) — PRF agility would resolve this
- Computational cost (FFT per range bin per CPI)
- Kaiser window trades velocity resolution for sidelobe suppression

**Real-world systems:** F-16 APG-68, F/A-18 APG-73, F-22 APG-77 (AESA), Eurofighter CAPTOR, all modern AESA fighter radars.
