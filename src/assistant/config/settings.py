import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    """Application-wide configuration loaded from environment variables."""

    default_city: str = "Katy"
    calendar_path: str = "./calendar.json"
    weather_api_timeout_seconds: int = 10


def load_settings() -> Settings:
    """Read optional env-var overrides and return a populated Settings instance.

    All keys are optional — the app runs with defaults when no env vars are set.
    """
    timeout_raw = os.environ.get("WEATHER_API_TIMEOUT_SECONDS")
    try:
        timeout = int(timeout_raw) if timeout_raw is not None else Settings.weather_api_timeout_seconds
    except ValueError:
        timeout = Settings.weather_api_timeout_seconds

    return Settings(
        default_city=os.environ.get("DEFAULT_CITY", Settings.default_city),
        calendar_path=os.environ.get("CALENDAR_PATH", Settings.calendar_path),
        weather_api_timeout_seconds=timeout,
    )
