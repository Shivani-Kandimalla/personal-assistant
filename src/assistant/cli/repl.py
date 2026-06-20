from typing import Callable

from assistant.advisor.engine import run_advisor
from assistant.calendar.loader import CalendarError, get_today_events
from assistant.cli.formatter import (
    format_advice,
    format_error,
    format_schedule,
    format_weather,
)
from assistant.config.settings import Settings
from assistant.weather.client import WeatherError, fetch_weather

_HELP_TEXT = """Available commands:
  weather <city>  — current temperature and 12-hour forecast
  schedule        — today's events from calendar.json
  advice          — weather + schedule recommendations
  help            — show this message
  exit / quit     — leave the assistant"""


def _cmd_weather(args: str, settings: Settings) -> str:
    """Handle the 'weather <city>' command."""
    city = args.strip()
    if not city:
        city = settings.default_city
    try:
        report = fetch_weather(city, timeout=settings.weather_api_timeout_seconds)
        return format_weather(report)
    except WeatherError as exc:
        return format_error(str(exc))


def _cmd_schedule(settings: Settings) -> str:
    """Handle the 'schedule' command."""
    try:
        events = get_today_events(settings.calendar_path)
        return format_schedule(events)
    except CalendarError as exc:
        return format_error(str(exc))


def _cmd_advice(settings: Settings) -> str:
    """Handle the 'advice' command — full weather + schedule pipeline."""
    try:
        events = get_today_events(settings.calendar_path)
    except CalendarError as exc:
        return format_error(str(exc))

    city = settings.default_city
    try:
        report = fetch_weather(city, timeout=settings.weather_api_timeout_seconds)
    except WeatherError as exc:
        return format_error(str(exc))

    advice_list = run_advisor(report, events)
    return format_advice(advice_list)


def repl(
    settings: Settings,
    input_fn: Callable[[], str] = input,
    print_fn: Callable[[str], None] = print,
) -> None:
    """Run the interactive REPL loop until the user types exit or quit.

    *input_fn* and *print_fn* are injectable for testing without stdin/stdout.
    """
    print_fn("Personal Assistant — type 'help' for commands.")
    while True:
        try:
            raw = input_fn("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print_fn("\nGoodbye.")
            break

        if not raw:
            continue

        parts = raw.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if command in ("exit", "quit"):
            print_fn("Goodbye.")
            break
        elif command == "help":
            print_fn(_HELP_TEXT)
        elif command == "weather":
            print_fn(_cmd_weather(args, settings))
        elif command == "schedule":
            print_fn(_cmd_schedule(settings))
        elif command == "advice":
            print_fn(_cmd_advice(settings))
        else:
            print_fn(format_error(f"Unknown command '{command}'. Type 'help' for available commands."))
