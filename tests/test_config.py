import pytest
from assistant.config.settings import Settings, load_settings


class TestSettingsDefaults:
    def test_default_city(self):
        s = Settings()
        assert s.default_city == "Katy"

    def test_default_calendar_path(self):
        s = Settings()
        assert s.calendar_path == "./calendar.json"

    def test_default_timeout(self):
        s = Settings()
        assert s.weather_api_timeout_seconds == 10


class TestLoadSettings:
    def test_returns_defaults_when_no_env_vars(self, monkeypatch):
        monkeypatch.delenv("DEFAULT_CITY", raising=False)
        monkeypatch.delenv("CALENDAR_PATH", raising=False)
        monkeypatch.delenv("WEATHER_API_TIMEOUT_SECONDS", raising=False)

        s = load_settings()
        assert s.default_city == "Katy"
        assert s.calendar_path == "./calendar.json"
        assert s.weather_api_timeout_seconds == 10

    def test_overrides_default_city(self, monkeypatch):
        monkeypatch.setenv("DEFAULT_CITY", "Austin, TX")
        s = load_settings()
        assert s.default_city == "Austin, TX"

    def test_overrides_calendar_path(self, monkeypatch):
        monkeypatch.setenv("CALENDAR_PATH", "/tmp/my_cal.json")
        s = load_settings()
        assert s.calendar_path == "/tmp/my_cal.json"

    def test_overrides_timeout(self, monkeypatch):
        monkeypatch.setenv("WEATHER_API_TIMEOUT_SECONDS", "30")
        s = load_settings()
        assert s.weather_api_timeout_seconds == 30

    def test_invalid_timeout_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("WEATHER_API_TIMEOUT_SECONDS", "not-a-number")
        s = load_settings()
        assert s.weather_api_timeout_seconds == 10
