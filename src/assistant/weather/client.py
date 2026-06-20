from typing import List, Optional
import requests

from .models import HourlySlot, WeatherReport

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# WMO weather interpretation codes → human-readable label
_WMO_CONDITIONS: dict[int, str] = {
    0: "Clear",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    80: "Rain showers", 81: "Rain showers", 82: "Heavy rain showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}


class WeatherError(Exception):
    """Raised when weather data cannot be fetched or parsed."""


def _condition_label(wmo_code: int) -> str:
    """Convert a WMO weather code to a readable string."""
    return _WMO_CONDITIONS.get(wmo_code, f"Unknown (code {wmo_code})")


def _strip_region_suffix(city: str) -> str:
    """Return only the city portion of a string like 'Austin, TX' or 'Paris, France'.

    Open-Meteo's geocoding API accepts plain city names only — state/country
    suffixes after a comma cause it to return no results.
    """
    return city.split(",")[0].strip()


def geocode(city: str, session: requests.Session, timeout: int) -> tuple[float, float, str]:
    """Resolve *city* to (latitude, longitude, resolved_label) via Open-Meteo Geocoding API.

    Strips state/country suffixes (e.g. ', TX') before querying because
    Open-Meteo only accepts plain city names.  Returns the fully qualified
    label from the API (e.g. 'Austin, Texas, United States') so callers
    always know which city was actually matched.
    Raises WeatherError for unknown city or network problems.
    """
    query = _strip_region_suffix(city)
    try:
        response = session.get(
            GEOCODE_URL,
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise WeatherError(
            "Couldn't reach the weather service — check your internet connection and try again."
        )
    except requests.exceptions.RequestException as exc:
        raise WeatherError(
            f"Weather service request failed: {exc}"
        ) from exc

    data = response.json()
    results = data.get("results")
    if not results:
        raise WeatherError(
            f"Unknown city '{city}'. Check the spelling and try again."
        )

    match = results[0]
    parts = [match.get("name", city)]
    if match.get("admin1"):
        parts.append(match["admin1"])
    if match.get("country"):
        parts.append(match["country"])
    resolved_label = ", ".join(parts)

    return float(match["latitude"]), float(match["longitude"]), resolved_label


def _fetch_forecast_data(
    lat: float,
    lon: float,
    session: requests.Session,
    timeout: int,
) -> dict:
    """Call the Open-Meteo Forecast API and return raw JSON."""
    try:
        response = session.get(
            FORECAST_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m",
                "hourly": "temperature_2m,precipitation_probability,wind_speed_10m,weather_code",
                "forecast_days": 1,
                "timezone": "auto",
            },
            timeout=timeout,
        )
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise WeatherError(
            "Couldn't reach the weather service — check your internet connection and try again."
        )
    except requests.exceptions.RequestException as exc:
        raise WeatherError(f"Weather service request failed: {exc}") from exc

    return response.json()


def _normalize(city: str, lat: float, lon: float, raw: dict) -> WeatherReport:
    """Normalize raw Open-Meteo forecast JSON into a WeatherReport."""
    try:
        current_temp = float(raw["current"]["temperature_2m"])
        hourly = raw["hourly"]
        times: List[str] = hourly["time"]
        temps: List[float] = hourly["temperature_2m"]
        precip: List[int] = hourly["precipitation_probability"]
        wind: List[float] = hourly["wind_speed_10m"]
        codes: List[int] = hourly["weather_code"]
    except (KeyError, TypeError) as exc:
        raise WeatherError(
            f"Unexpected response format from weather service: {exc}"
        ) from exc

    slots = [
        HourlySlot(
            time=times[i],
            temp_c=float(temps[i]),
            precipitation_probability=int(precip[i]),
            wind_speed_kmh=float(wind[i]),
            condition=_condition_label(int(codes[i])),
        )
        for i in range(len(times))
    ]

    return WeatherReport(
        city=city,
        latitude=lat,
        longitude=lon,
        current_temp_c=current_temp,
        hourly=slots,
    )


def fetch_weather(
    city: str,
    timeout: int = 10,
    session: Optional[requests.Session] = None,
) -> WeatherReport:
    """Fetch and return a normalised WeatherReport for *city*.

    Uses Open-Meteo (no API key required).  Pass a custom *session* to
    enable monkeypatching in tests without live network calls.
    """
    sess = session or requests.Session()
    lat, lon, resolved_label = geocode(city, sess, timeout)
    raw = _fetch_forecast_data(lat, lon, sess, timeout)
    return _normalize(resolved_label, lat, lon, raw)
