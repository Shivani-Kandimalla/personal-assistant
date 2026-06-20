from dataclasses import dataclass, field
from typing import List


@dataclass
class HourlySlot:
    """One hour of forecast data."""

    time: str                       # ISO 8601 local datetime string e.g. "2026-06-18T07:00"
    temp_c: float
    precipitation_probability: int  # 0–100
    wind_speed_kmh: float
    condition: str                  # human-readable, e.g. "Rain", "Clear"


@dataclass
class WeatherReport:
    """Normalised forecast for a city, as defined in PRD §5.2."""

    city: str
    latitude: float
    longitude: float
    current_temp_c: float
    hourly: List[HourlySlot] = field(default_factory=list)
