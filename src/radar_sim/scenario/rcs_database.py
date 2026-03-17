"""
Approximate RCS values for common aircraft types.

Values are rough averages at X-band, nose-on aspect unless noted.
Real RCS varies enormously with aspect angle, frequency, and whether
the aircraft has radar-absorbent treatment.  These are APPROXIMATE
and PUBLICLY AVAILABLE estimates for educational purposes only.

Sources: Skolnik, Stimson, publicly available estimates.
All values in m^2.
"""

RCS_DATABASE: dict[str, float] = {
    # Fighters
    "F-16": 1.2,
    "F-15": 5.0,
    "F/A-18": 1.0,
    "Su-27": 10.0,
    "MiG-29": 3.0,
    "MiG-21": 3.5,
    "F-22": 0.0001,       # stealth
    "F-35": 0.001,        # stealth
    "Su-57": 0.1,         # reduced RCS
    # Bombers
    "B-52": 100.0,
    "Tu-95": 80.0,
    "B-1B": 1.0,          # reduced RCS design
    "B-2": 0.0001,        # stealth
    # Transport / AWACS
    "C-130": 40.0,
    "E-3 Sentry": 50.0,
    "Boeing 737": 20.0,
    # Missiles
    "Cruise missile": 0.1,
    "Anti-ship missile": 0.1,
    "Ballistic RV": 0.01,
    # UAVs
    "MQ-9 Reaper": 1.0,
    "RQ-170 Sentinel": 0.01,
    "Small UAV": 0.01,
    # Helicopters
    "AH-64 Apache": 10.0,
    "UH-60 Black Hawk": 15.0,
    "Mi-24 Hind": 20.0,
    # Other
    "Bird (large)": 0.01,
    "Bird (small)": 0.001,
    "Chaff cloud": 50.0,
}
