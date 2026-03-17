"""
Core data models for the radar simulation.
All units are SI unless noted: meters, seconds, Hz, Watts, m/s.
"""

from dataclasses import dataclass, field
from enum import Enum
import numpy as np


# ─── Constants ───────────────────────────────────────────────────────
C = 299_792_458.0          # speed of light (m/s)
K_BOLTZ = 1.380649e-23     # Boltzmann constant (J/K)


# ─── Target ──────────────────────────────────────────────────────────
@dataclass
class Target:
    """A single airborne target in the scenario."""
    id: str
    x: float                # position east (m)
    y: float                # position north (m)
    altitude: float         # altitude (m)
    vx: float               # velocity east (m/s)
    vy: float               # velocity north (m/s)
    rcs: float              # radar cross-section (m^2), constant for now
    label: str = "unknown"  # e.g. "fighter", "bomber", "missile"

    def update(self, dt: float):
        """Advance target position by dt seconds."""
        self.x += self.vx * dt
        self.y += self.vy * dt

    @property
    def speed(self) -> float:
        return np.sqrt(self.vx**2 + self.vy**2)

    @property
    def heading_rad(self) -> float:
        return np.arctan2(self.vx, self.vy)


# ─── Radar Parameters ───────────────────────────────────────────────
@dataclass
class RadarParams:
    """
    Defines the radar system.
    Defaults loosely inspired by an X-band fighter radar (Sapfir-23ML class).
    """
    # Transmitter
    frequency: float = 10.0e9       # operating frequency (Hz), X-band
    power: float = 50000.0          # peak transmit power (W) — 50 kW, typical fighter radar
    pulse_width: float = 1.0e-6     # pulse width (s) — 1 µs
    prf: float = 2000.0             # pulse repetition frequency (Hz)

    # Antenna
    gain_db: float = 33.0           # antenna gain (dBi)
    beamwidth_az: float = 3.0       # azimuth beamwidth (degrees)
    beamwidth_el: float = 5.0       # elevation beamwidth (degrees)
    scan_rate: float = 60.0         # scan rate (deg/s) — for TWS

    # Receiver
    noise_figure_db: float = 4.0    # receiver noise figure (dB)
    system_temp: float = 290.0      # system temperature (K)
    bandwidth: float = 1.0e6        # receiver bandwidth (Hz), matched to 1/pulse_width

    # Detection
    detection_threshold_db: float = 13.0  # required SNR for detection (dB)

    @property
    def wavelength(self) -> float:
        return C / self.frequency

    @property
    def gain_linear(self) -> float:
        return 10 ** (self.gain_db / 10)

    @property
    def noise_figure_linear(self) -> float:
        return 10 ** (self.noise_figure_db / 10)

    @property
    def noise_power(self) -> float:
        """Thermal noise power at receiver (W)."""
        return K_BOLTZ * self.system_temp * self.bandwidth * self.noise_figure_linear

    @property
    def max_unambiguous_range(self) -> float:
        """Max unambiguous range (m) given PRF."""
        return C / (2 * self.prf)

    @property
    def range_resolution(self) -> float:
        """Range resolution (m) from pulse width."""
        return C * self.pulse_width / 2

    @property
    def max_unambiguous_velocity(self) -> float:
        """Max unambiguous velocity (m/s) — ±λ·PRF/4."""
        return self.wavelength * self.prf / 4

    @property
    def blind_speeds(self) -> list[float]:
        """First 5 blind speeds for MTI (m/s)."""
        return [n * self.wavelength * self.prf / 2 for n in range(1, 6)]


# ─── Radar Position ─────────────────────────────────────────────────
@dataclass
class RadarPosition:
    """Where the radar is in the world."""
    x: float = 0.0
    y: float = 0.0
    altitude: float = 5000.0   # airborne radar at 5 km
    heading: float = 0.0       # antenna boresight heading (rad), 0 = north


# ─── Clutter Model ──────────────────────────────────────────────────
@dataclass
class ClutterParams:
    """Simple ground clutter model parameters."""
    reflectivity_db: float = -20.0   # terrain backscatter coeff (dB per m^2)
    enabled: bool = True

    @property
    def reflectivity_linear(self) -> float:
        return 10 ** (self.reflectivity_db / 10)


# ─── Detection (output of a mode's processing) ──────────────────────
@dataclass
class Detection:
    """A single detection output from a radar mode."""
    range_m: float                 # detected range (m)
    azimuth_deg: float = 0.0      # detected azimuth (deg) — for future use
    velocity_mps: float | None = None   # radial velocity if available
    snr_db: float = 0.0           # signal-to-noise ratio at detection
    target_id: str | None = None  # ground truth ID (for debugging/display)
    is_clutter: bool = False      # whether this detection is a clutter return
    is_ambiguous: bool = False    # range-ambiguous (true range > R_unamb)


# ─── Radar Mode Enum ─────────────────────────────────────────────────
class RadarMode(Enum):
    SRC = "src"
    MTI = "mti"
    PULSE_DOPPLER = "pulse_doppler"
    TWS = "tws"


# ─── Raw Return (intermediate data between physics and mode) ────────
@dataclass
class RawReturn:
    """
    A single raw return from one scatterer (target or clutter cell).
    This is what the physics engine produces; modes process these.
    """
    range_m: float
    radial_velocity: float       # radial velocity toward radar (m/s), positive = closing
    received_power: float        # received power (W)
    doppler_hz: float            # Doppler shift (Hz)
    target_id: str | None = None # None for clutter
    is_clutter: bool = False
