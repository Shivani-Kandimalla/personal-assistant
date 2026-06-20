import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from assistant.advisor.models import Advice
from assistant.calendar.models import Event
from assistant.cli.formatter import (
    format_advice,
    format_error,
    format_schedule,
    format_weather,
)
from assistant.cli.repl import repl
from assistant.config.settings import Settings
from assistant.weather.client import WeatherError
from assistant.calendar.loader import CalendarError
from assistant.weather.models import HourlySlot, WeatherReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_settings(**kwargs) -> Settings:
    defaults = dict(default_city="TestCity", calendar_path="./calendar.json", weather_api_timeout_seconds=10)
    defaults.update(kwargs)
    return Settings(**defaults)


def make_report() -> WeatherReport:
    return WeatherReport(
        city="TestCity",
        latitude=0.0,
        longitude=0.0,
        current_temp_c=21.5,
        hourly=[
            HourlySlot("2026-06-18T07:00", 20.0, 5, 10.0, "Clear"),
            HourlySlot("2026-06-18T08:00", 21.0, 10, 12.0, "Partly cloudy"),
        ],
    )


def make_event(title="Morning Run", start="2026-06-18T07:00:00", end="2026-06-18T07:45:00", location="Riverside Park") -> Event:
    return Event(title=title, start=datetime.fromisoformat(start), end=datetime.fromisoformat(end), location=location)


# ---------------------------------------------------------------------------
# format_weather
# ---------------------------------------------------------------------------

class TestFormatWeather:
    def test_contains_city_name(self):
        out = format_weather(make_report())
        assert "TestCity" in out

    def test_contains_current_temp(self):
        out = format_weather(make_report())
        assert "21.5" in out

    def test_contains_hourly_slots(self):
        out = format_weather(make_report())
        assert "Clear" in out
        assert "Partly cloudy" in out

    def test_empty_hourly_shows_fallback(self):
        report = WeatherReport("X", 0.0, 0.0, 15.0, hourly=[])
        out = format_weather(report)
        assert "No hourly data" in out


# ---------------------------------------------------------------------------
# format_schedule
# ---------------------------------------------------------------------------

class TestFormatSchedule:
    def test_lists_event_title(self):
        out = format_schedule([make_event()])
        assert "Morning Run" in out

    def test_shows_times(self):
        out = format_schedule([make_event()])
        assert "07:00" in out

    def test_empty_schedule_message(self):
        out = format_schedule([])
        assert "No events" in out

    def test_shows_location(self):
        out = format_schedule([make_event()])
        assert "Riverside Park" in out


# ---------------------------------------------------------------------------
# format_advice
# ---------------------------------------------------------------------------

class TestFormatAdvice:
    def test_warning_prefix(self):
        items = [Advice(severity="warning", message="Bring rain gear.", related_event="Run")]
        out = format_advice(items)
        assert out.startswith("[!]")

    def test_info_prefix(self):
        items = [Advice(severity="info", message="Layer up.", related_event=None)]
        out = format_advice(items)
        assert out.startswith("[i]")

    def test_empty_list_returns_all_clear(self):
        out = format_advice([])
        assert "[i]" in out
        assert "fine" in out.lower()

    def test_multiple_items_each_on_own_line(self):
        items = [
            Advice(severity="warning", message="Rain.", related_event="Run"),
            Advice(severity="info", message="Hot.", related_event="Lunch"),
        ]
        lines = format_advice(items).splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# format_error
# ---------------------------------------------------------------------------

class TestFormatError:
    def test_prefixed_with_bang(self):
        out = format_error("Something went wrong.")
        assert out.startswith("[!]")
        assert "Something went wrong." in out


# ---------------------------------------------------------------------------
# repl — command dispatch
# ---------------------------------------------------------------------------

class TestRepl:
    def _run(self, commands: list, patches: dict = None) -> list:
        """Drive the REPL with a list of input lines; return printed output lines."""
        inputs = iter(commands + ["exit"])
        outputs = []
        settings = make_settings()

        ctx = {}
        if patches:
            ctx = patches

        with patch.dict("sys.modules", {}):
            repl(settings, input_fn=lambda _="": next(inputs), print_fn=outputs.append, **ctx)
        return outputs

    def test_help_command(self):
        inputs = iter(["help", "exit"])
        outputs = []
        repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("weather" in line for line in outputs)
        assert any("schedule" in line for line in outputs)

    def test_exit_command(self):
        inputs = iter(["exit"])
        outputs = []
        repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("Goodbye" in line for line in outputs)

    def test_quit_command(self):
        inputs = iter(["quit"])
        outputs = []
        repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("Goodbye" in line for line in outputs)

    def test_unknown_command_shows_error(self):
        inputs = iter(["foobar", "exit"])
        outputs = []
        repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("[!]" in line and "foobar" in line for line in outputs)

    def test_weather_command_success(self):
        inputs = iter(["weather Paris", "exit"])
        outputs = []
        with patch("assistant.cli.repl.fetch_weather", return_value=make_report()):
            repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("TestCity" in line or "21.5" in line for line in outputs)

    def test_weather_command_error_shows_message(self):
        inputs = iter(["weather NoCity", "exit"])
        outputs = []
        with patch("assistant.cli.repl.fetch_weather", side_effect=WeatherError("Unknown city 'NoCity'.")):
            repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("[!]" in line for line in outputs)

    def test_schedule_command_success(self):
        inputs = iter(["schedule", "exit"])
        outputs = []
        with patch("assistant.cli.repl.get_today_events", return_value=[make_event()]):
            repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("Morning Run" in line for line in outputs)

    def test_schedule_command_calendar_error(self):
        inputs = iter(["schedule", "exit"])
        outputs = []
        with patch("assistant.cli.repl.get_today_events", side_effect=CalendarError("File not found.")):
            repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("[!]" in line for line in outputs)

    def test_advice_command_no_events_shows_r6(self):
        inputs = iter(["advice", "exit"])
        outputs = []
        with patch("assistant.cli.repl.get_today_events", return_value=[]), \
             patch("assistant.cli.repl.fetch_weather", return_value=make_report()):
            repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("no events" in line.lower() for line in outputs)

    def test_advice_command_weather_error_shows_message(self):
        inputs = iter(["advice", "exit"])
        outputs = []
        with patch("assistant.cli.repl.get_today_events", return_value=[make_event()]), \
             patch("assistant.cli.repl.fetch_weather", side_effect=WeatherError("Timeout.")):
            repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("[!]" in line for line in outputs)

    def test_empty_input_does_not_crash(self):
        inputs = iter(["", "exit"])
        outputs = []
        repl(make_settings(), input_fn=lambda _="": next(inputs), print_fn=outputs.append)
        assert any("Goodbye" in line for line in outputs)

    def test_eof_exits_gracefully(self):
        outputs = []
        repl(make_settings(), input_fn=lambda _="": (_ for _ in ()).throw(EOFError()), print_fn=outputs.append)
        assert any("Goodbye" in line for line in outputs)
