"""SIMULATED traffic model (no Streamlit code).

This is the same model and random seed used by the Home page and the Traffic Map,
so the numbers match. It is NOT live traffic. Pages can import it from here
instead of copying the code.
"""

import numpy as np
import pandas as pd

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# name: (latitude, longitude, multiplier). Multipliers are OUR ASSUMPTIONS.
AREAS = {
    "Godowlia / Dashashwamedh": (25.3092, 83.0104, 1.25),
    "Lanka (BHU)": (25.2814, 82.9916, 1.10),
    "Cantonment": (25.3270, 82.9880, 1.05),
    "Sigra": (25.3150, 82.9800, 1.00),
    "Rathyatra": (25.3160, 82.9930, 0.95),
    "Kachehri": (25.3337, 82.9847, 0.95),
    "Assi Ghat": (25.2880, 83.0060, 0.90),
    "Maduadih": (25.3380, 82.9600, 0.85),
    "Pandeypur": (25.3450, 82.9650, 0.80),
    "Sarnath": (25.3809, 83.0240, 0.70),
}


def _bump(hour: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-((hour - centre) ** 2) / (2 * width**2))


def _daily_profile(is_weekend: bool) -> np.ndarray:
    h = np.arange(24, dtype=float)
    if is_weekend:
        return 10 + 30 * _bump(h, 11, 2.5) + 45 * _bump(h, 18.5, 2.5)
    return 12 + 52 * _bump(h, 9, 1.6) + 25 * _bump(h, 13, 2.0) + 58 * _bump(h, 18, 1.9)


def build_simulation() -> pd.DataFrame:
    """One row per (area, day, hour) with a SIMULATED congestion index (0-100)."""
    rng = np.random.default_rng(42)  # fixed seed -> same numbers every run
    rows = []
    for area, (_, _, factor) in AREAS.items():
        for d, day in enumerate(DAYS):
            profile = _daily_profile(is_weekend=d >= 5)
            day_factor = {4: 1.04, 6: 0.92}.get(d, 1.0)
            values = profile * factor * day_factor + rng.normal(0, 3, 24)
            for hour, value in enumerate(np.clip(values, 0, 100)):
                rows.append((area, day, hour, round(float(value), 1)))
    return pd.DataFrame(rows, columns=["area", "day", "hour", "congestion_index"])


def city_index(sim: pd.DataFrame, day: str, hour: int) -> float:
    """Average SIMULATED congestion index over all areas for one day and hour."""
    part = sim[(sim["day"] == day) & (sim["hour"] == hour)]
    return float(part["congestion_index"].mean())
