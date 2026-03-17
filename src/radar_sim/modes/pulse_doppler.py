"""
Pulse Doppler (PD) Mode — signal-level coherent processing.

Unlike SRC and MTI which operate on abstract power values, PD synthesises
the complex slow-time signal for each range bin across a Coherent Processing
Interval (CPI) of N pulses, then applies an FFT to resolve both range and
Doppler (velocity) simultaneously.

Processing chain:
    1. Range-bin the raw returns (folding for range ambiguity)
    2. For each range bin, build the complex slow-time signal:
         s[n] = Σ_k  A_k · exp(j·2π·f_dk·n / PRF)  +  noise[n]
    3. Window and FFT across the pulse dimension → Doppler spectrum
    4. Apply a clutter notch (zero out near-DC Doppler bins)
    5. CA-CFAR detection on the range-Doppler map
    6. Convert (range_bin, doppler_bin) → (range_m, velocity_mps)
       and flag range-ambiguous detections

Advantages over MTI:
    - No blind speeds (clutter notch is narrowband, not periodic nulls)
    - Provides calibrated velocity measurements
    - Higher processing gain from coherent integration (N pulses)

Tradeoff:
    - High PRF required → range ambiguity (R_unamb = c / 2·PRF)
    - Targets beyond R_unamb fold into the unambiguous interval
"""

import numpy as np
from radar_sim.models import RawReturn, Detection, RadarParams, C
from radar_sim.modes.base_mode import BaseMode


class PulseDopplerMode(BaseMode):
    """
    Coherent Pulse Doppler processor.

    Builds a range-Doppler map via slow-time FFT, applies a clutter notch
    around zero Doppler, and uses Cell-Averaging CFAR to produce detections
    with both range and velocity.

    Parameters
    ----------
    radar : RadarParams
        System parameters (frequency, PRF, power, noise, etc.).
    n_pulses : int
        Number of pulses in the CPI.  More pulses → finer velocity resolution
        (Δv = λ·PRF / 2N) but slower update rate.
    notch_half_width : int
        Number of Doppler bins on *each side* of DC to zero out.
        Total notch width = 2·notch_half_width + 1 bins.
    threshold_db : float | None
        CFAR detection threshold in dB above the local noise estimate.
        Defaults to the radar's detection_threshold_db.
    """

    def __init__(
        self,
        radar: RadarParams,
        n_pulses: int = 64,
        notch_half_width: int = 5,
        threshold_db: float | None = None,
    ):
        super().__init__(radar)
        self.n_pulses = n_pulses
        self.notch_half_width = notch_half_width
        self.threshold_db = (
            threshold_db if threshold_db is not None else radar.detection_threshold_db
        )

        # Pre-compute Kaiser window (β=14 gives ~80 dB sidelobe suppression,
        # critical for rejecting close-range clutter spectral leakage)
        self._window = np.kaiser(self.n_pulses, 14.0)
        self._window_sq_sum = float(np.sum(self._window ** 2))

    # ── properties ────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return f"PD (Pulse Doppler, {self.n_pulses} pulses)"

    @property
    def description(self) -> str:
        return (
            "Coherent pulse Doppler processing with clutter notch and CFAR. "
            "Provides range and velocity, no blind speeds."
        )

    @property
    def velocity_resolution(self) -> float:
        """Velocity resolution (m/s) set by CPI length: Δv = λ·PRF / (2·N)."""
        return self.radar.wavelength * self.radar.prf / (2 * self.n_pulses)

    @property
    def doppler_bin_width_hz(self) -> float:
        """Doppler bin spacing (Hz): PRF / N."""
        return self.radar.prf / self.n_pulses

    # ── helpers ───────────────────────────────────────────────────────

    def _alias_doppler(self, doppler_hz: float | np.ndarray) -> float | np.ndarray:
        """Alias a Doppler frequency into [-PRF/2, PRF/2).

        After sampling at PRF, true Doppler folds:
            f_aliased = f_true mod PRF,  mapped to [-PRF/2, PRF/2)
        This is needed so ground-truth association compares frequencies
        in the same aliased domain that the FFT output uses.
        """
        prf = self.radar.prf
        aliased = np.mod(doppler_hz, prf)
        return np.where(aliased >= prf / 2, aliased - prf, aliased)

    # ── range-Doppler map (public — useful for visualisation) ─────────

    def build_range_doppler_map(
        self, raw_returns: list[RawReturn]
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[list[RawReturn]]]:
        """
        Construct the range-Doppler power map from raw returns.

        For each range bin the slow-time signal is synthesised by summing
        complex sinusoids at each scatterer's Doppler frequency, then adding
        thermal noise.  A Kaiser window (β=14) is applied before the FFT to
        suppress spectral sidelobes to ~-80 dB, preventing strong close-range
        clutter from leaking across the entire Doppler spectrum.

        Returns
        -------
        power_map : ndarray, shape (n_range_bins, n_pulses)
            Power (|X[k]|²) in each range-Doppler cell.
        range_centers_m : ndarray, shape (n_range_bins,)
            Centre range of each range bin (m).
        doppler_freqs_hz : ndarray, shape (n_pulses,)
            Doppler frequency axis (Hz), zero-centred via fftshift.
        bin_scatterers : list[list[RawReturn]]
            The raw returns assigned to each range bin (for ground-truth
            association after detection).
        """
        range_res = self.radar.range_resolution
        r_unamb = self.radar.max_unambiguous_range
        n_range_bins = int(r_unamb / range_res)

        # --- assign returns to range bins (fold for ambiguity) ------------
        bin_scatterers: list[list[RawReturn]] = [[] for _ in range(n_range_bins)]
        for ret in raw_returns:
            folded_range = ret.range_m % r_unamb
            idx = int(folded_range / range_res)
            if 0 <= idx < n_range_bins:
                bin_scatterers[idx].append(ret)

        # --- synthesise slow-time signal per range bin --------------------
        pulse_idx = np.arange(self.n_pulses)                    # n = 0 … N-1
        slow_time = np.zeros((n_range_bins, self.n_pulses), dtype=np.complex128)

        for i, scatterers in enumerate(bin_scatterers):
            if scatterers:
                # Vectorise over all scatterers in this bin at once
                amps = np.array([np.sqrt(s.received_power) for s in scatterers])
                f_d  = np.array([s.doppler_hz for s in scatterers])

                # phase(n_scatterers, n_pulses) = 2π · f_d · n / PRF
                phases = 2.0 * np.pi * np.outer(f_d, pulse_idx) / self.radar.prf

                # sum of complex sinusoids → (n_pulses,)
                slow_time[i, :] = (amps[:, np.newaxis] * np.exp(1j * phases)).sum(axis=0)

        # Add complex Gaussian noise (independent per range bin & pulse)
        # noise ~ CN(0, noise_power)  →  I,Q each ~ N(0, noise_power/2)
        noise_std = np.sqrt(self.radar.noise_power / 2.0)
        slow_time += noise_std * (
            np.random.randn(n_range_bins, self.n_pulses)
            + 1j * np.random.randn(n_range_bins, self.n_pulses)
        )

        # --- window + FFT ------------------------------------------------
        spectrum = np.fft.fftshift(
            np.fft.fft(slow_time * self._window[np.newaxis, :], axis=1),
            axes=1,
        )

        power_map = np.abs(spectrum) ** 2

        # --- axes ---------------------------------------------------------
        range_centers_m = (np.arange(n_range_bins) + 0.5) * range_res
        doppler_freqs_hz = np.fft.fftshift(
            np.fft.fftfreq(self.n_pulses, d=1.0 / self.radar.prf)
        )

        return power_map, range_centers_m, doppler_freqs_hz, bin_scatterers

    # ── CFAR detection ────────────────────────────────────────────────

    def _cfar_threshold_map(
        self,
        power_map: np.ndarray,
        notch_mask: np.ndarray,
        guard: int = 6,
        training: int = 12,
    ) -> np.ndarray:
        """
        Cell-Averaging CFAR along the Doppler dimension.

        For each cell (range_bin, doppler_bin) the local noise floor is
        estimated from training cells ±(guard+1 … guard+training) bins
        away in Doppler (circular, since Doppler wraps at ±PRF/2).
        Training cells that fall inside the clutter notch are excluded
        so their zeroed power doesn't artificially lower the estimate.

        The detection threshold per cell is  α · noise_estimate  where
        α = 10^(threshold_db / 10).  A hard minimum threshold based on
        thermal noise is also enforced.
        """
        n_range, n_doppler = power_map.shape
        alpha = 10.0 ** (self.threshold_db / 10.0)

        # Training cell offsets (symmetric, circular)
        pos_offsets = np.arange(guard + 1, guard + training + 1)
        neg_offsets = np.arange(-(guard + training), -guard)
        offsets = np.concatenate([pos_offsets, neg_offsets])   # (2*training,)

        # For each Doppler bin j, find the training cell indices
        j_idx = np.arange(n_doppler)
        train_idx = (j_idx[:, np.newaxis] + offsets[np.newaxis, :]) % n_doppler
        # train_idx shape: (n_doppler, 2*training)

        # Mask out training cells that fall inside the notch
        valid = ~notch_mask[train_idx]                          # (D, 2T)
        n_valid = np.maximum(valid.sum(axis=1), 1)              # (D,)

        # Gather training-cell power and zero out notched cells
        train_power = power_map[:, train_idx] * valid[np.newaxis, :, :]
        # train_power shape: (R, D, 2T)

        # Noise estimate = mean of valid training cells
        noise_est = train_power.sum(axis=2) / n_valid[np.newaxis, :]  # (R, D)

        # Hard floor: thermal noise after windowed FFT
        min_thresh = alpha * self.radar.noise_power * self._window_sq_sum

        return np.maximum(alpha * noise_est, min_thresh)

    # ── main processing entry point ──────────────────────────────────

    def process(self, raw_returns: list[RawReturn]) -> list[Detection]:
        """
        Full PD processing chain.

        1. Build range-Doppler map  (signal synthesis → FFT)
        2. Apply clutter notch      (zero Doppler bins near DC)
        3. CA-CFAR detection        (adaptive threshold per cell)
        4. Map detections → (range_m, velocity_mps), flag ambiguous ranges
        """
        r_unamb = self.radar.max_unambiguous_range

        # 1. range-Doppler map
        power_map, range_centers, doppler_freqs, bin_scatterers = (
            self.build_range_doppler_map(raw_returns)
        )

        # 2. clutter notch — zero out ±notch_half_width bins around DC
        centre = self.n_pulses // 2
        lo = max(0, centre - self.notch_half_width)
        hi = min(self.n_pulses, centre + self.notch_half_width + 1)
        notch_mask = np.zeros(self.n_pulses, dtype=bool)
        notch_mask[lo:hi] = True
        power_map[:, notch_mask] = 0.0

        # 3. CA-CFAR detection (adaptive threshold per range-Doppler cell)
        threshold_map = self._cfar_threshold_map(power_map, notch_mask)
        noise_floor = self.radar.noise_power * self._window_sq_sum

        # Detect: above CFAR threshold AND outside the notch
        det_ri, det_di = np.nonzero(
            (power_map > threshold_map) & ~notch_mask[np.newaxis, :]
        )

        # 4. build Detection objects
        detections: list[Detection] = []
        for ri, di in zip(det_ri, det_di):
            range_m = float(range_centers[ri])
            doppler_hz = float(doppler_freqs[di])
            velocity_mps = doppler_hz * self.radar.wavelength / 2.0
            snr_db = float(
                10.0 * np.log10(power_map[ri, di] / noise_floor)
                if noise_floor > 0
                else 0.0
            )

            # Ground-truth association: compare ALIASED Doppler frequencies.
            # The detected Doppler lives in [-PRF/2, PRF/2) (post-FFT),
            # but the raw return stores the true (unaliased) Doppler.
            # We must alias both to the same domain before comparing.
            scatterers = bin_scatterers[ri]
            target_id: str | None = None
            is_clutter = False
            is_ambiguous = False
            azimuth_deg = 0.0

            if scatterers:
                aliased_dopplers = self._alias_doppler(
                    np.array([s.doppler_hz for s in scatterers])
                )
                diffs = np.abs(aliased_dopplers - doppler_hz)
                best = scatterers[int(np.argmin(diffs))]
                target_id = best.target_id
                is_clutter = best.is_clutter
                is_ambiguous = best.range_m > r_unamb
                azimuth_deg = best.azimuth_deg

            detections.append(Detection(
                range_m=range_m,
                azimuth_deg=azimuth_deg,
                velocity_mps=velocity_mps,
                snr_db=snr_db,
                target_id=target_id,
                is_clutter=is_clutter,
                is_ambiguous=is_ambiguous,
            ))

        return detections
