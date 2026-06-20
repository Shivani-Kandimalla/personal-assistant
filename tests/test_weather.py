import pytest
import requests
from unittest.mock import MagicMock, patch

from assistant.weather.client import (
    geocode,
    fetch_weather,
    WeatherError,
    _normalize,
    _condition_label,
    _strip_region_suffix,
)
from assistant.weather.models import WeatherReport, HourlySlot


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def make_session(geocode_json: dict, forecast_json: dict) -> requests.Session:
    """Return a mock Session whose .get() returns preset payloads in order."""
    session = MagicMock(spec=requests.Session)
    geo_resp = MagicMock()
    geo_resp.json.return_value = geocode_json
    geo_resp.raise_for_status.return_value = None

    forecast_resp = MagicMock()
    forecast_resp.json.return_value = forecast_json
    forecast_resp.raise_for_status.return_value = None

    session.get.side_effect = [geo_resp, forecast_resp]
    return session


GEO_OK = {"results": [{"name": "New York", "admin1": "New York", "country": "United States", "latitude": 40.71, "longitude": -74.01}]}

FORECAST_OK = {
    "current": {"temperature_2m": 18.5},
    "hourly": {
        "time": ["2026-06-18T07:00", "2026-06-18T08:00"],
        "temperature_2m": [17.0, 18.0],
        "precipitation_probability": [10, 20],
        "wind_speed_10m": [12.0, 15.0],
        "weather_code": [0, 61],
    },
}


# ---------------------------------------------------------------------------
# _strip_region_suffix
# ---------------------------------------------------------------------------

class TestStripRegionSuffix:
    def test_strips_state_abbreviation(self):
        assert _strip_region_suffix("Austin, TX") == "Austin"

    def test_strips_full_country(self):
        assert _strip_region_suffix("Paris, France") == "Paris"

    def test_plain_city_unchanged(self):
        assert _strip_region_suffix("London") == "London"

    def test_strips_whitespace(self):
        assert _strip_region_suffix("  Austin , TX  ") == "Austin"


# ---------------------------------------------------------------------------
# _condition_label
# ---------------------------------------------------------------------------

class TestConditionLabel:
    def test_known_code_clear(self):
        assert _condition_label(0) == "Clear"

    def test_known_code_rain(self):
        assert _condition_label(61) == "Light rain"

    def test_unknown_code_returns_fallback(self):
        assert "Unknown" in _condition_label(999)


# ---------------------------------------------------------------------------
# geocode
# ---------------------------------------------------------------------------

class TestGeocode:
    def test_returns_lat_lon_and_label_for_known_city(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.json.return_value = GEO_OK
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        lat, lon, label = geocode("New York", session, timeout=10)
        assert lat == pytest.approx(40.71)
        assert lon == pytest.approx(-74.01)
        assert "New York" in label
        assert "United States" in label

    def test_resolved_label_includes_region_and_country(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.json.return_value = {"results": [{"name": "Austin", "admin1": "Texas", "country": "United States", "latitude": 30.27, "longitude": -97.74}]}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        _, _, label = geocode("Austin, TX", session, timeout=10)
        assert label == "Austin, Texas, United States"

    def test_resolved_label_graceful_without_admin1(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.json.return_value = {"results": [{"name": "London", "country": "United Kingdom", "latitude": 51.51, "longitude": -0.13}]}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        _, _, label = geocode("London", session, timeout=10)
        assert label == "London, United Kingdom"

    def test_unknown_city_raises_weather_error(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.json.return_value = {"results": None}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        with pytest.raises(WeatherError, match="Unknown city"):
            geocode("ZZZNowhere", session, timeout=10)

    def test_empty_results_raises_weather_error(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.json.return_value = {}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        with pytest.raises(WeatherError, match="Unknown city"):
            geocode("NoCity", session, timeout=10)

    def test_timeout_raises_weather_error(self):
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(WeatherError, match="internet connection"):
            geocode("New York", session, timeout=1)

    def test_request_exception_raises_weather_error(self):
        session = MagicMock(spec=requests.Session)
        session.get.side_effect = requests.exceptions.ConnectionError("refused")

        with pytest.raises(WeatherError, match="request failed"):
            geocode("New York", session, timeout=10)


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_returns_weather_report(self):
        report = _normalize("New York", 40.71, -74.01, FORECAST_OK)
        assert isinstance(report, WeatherReport)
        assert report.city == "New York"
        assert report.current_temp_c == pytest.approx(18.5)
        assert len(report.hourly) == 2

    def test_hourly_slots_populated(self):
        report = _normalize("New York", 40.71, -74.01, FORECAST_OK)
        slot = report.hourly[0]
        assert isinstance(slot, HourlySlot)
        assert slot.time == "2026-06-18T07:00"
        assert slot.temp_c == pytest.approx(17.0)
        assert slot.precipitation_probability == 10
        assert slot.wind_speed_kmh == pytest.approx(12.0)
        assert slot.condition == "Clear"

    def test_malformed_response_raises_weather_error(self):
        with pytest.raises(WeatherError, match="Unexpected response format"):
            _normalize("New York", 40.71, -74.01, {"bad": "data"})


# ---------------------------------------------------------------------------
# fetch_weather (full pipeline)
# ---------------------------------------------------------------------------

class TestFetchWeather:
    def test_happy_path_returns_report(self):
        session = make_session(GEO_OK, FORECAST_OK)
        report = fetch_weather("New York", timeout=10, session=session)
        assert "New York" in report.city
        assert "United States" in report.city   # resolved label shown
        assert report.current_temp_c == pytest.approx(18.5)
        assert len(report.hourly) == 2

    def test_unknown_city_propagates_weather_error(self):
        session = MagicMock(spec=requests.Session)
        resp = MagicMock()
        resp.json.return_value = {"results": []}
        resp.raise_for_status.return_value = None
        session.get.return_value = resp

        with pytest.raises(WeatherError, match="Unknown city"):
            fetch_weather("NoCity", timeout=10, session=session)
