from typing import List

from assistant.advisor.models import Advice
from assistant.calendar.models import Event
from assistant.weather.models import WeatherReport

_SEVERITY_PREFIX = {"warning": "[!]", "info": "[i]"}
_MAX_HOURLY_DISPLAY = 12


def format_weather(report: WeatherReport) -> str:
    """Render a WeatherReport as a multi-line string for CLI output."""
    lines = [
        f"Weather for {report.city}",
        f"  Current: {report.current_temp_c:.1f}°C",
        f"  Next {_MAX_HOURLY_DISPLAY}h forecast:",
    ]
    for slot in report.hourly[:_MAX_HOURLY_DISPLAY]:
        lines.append(
            f"    {slot.time[-5:]}  {slot.temp_c:.1f}°C  "
            f"{slot.condition}  "
            f"Precip {slot.precipitation_probability}%  "
            f"Wind {slot.wind_speed_kmh:.0f} km/h"
        )
    if not report.hourly:
        lines.append("    No hourly data available.")
    return "\n".join(lines)


def format_schedule(events: List[Event]) -> str:
    """Render today's event list as a multi-line string for CLI output."""
    if not events:
        return "No events scheduled for today."
    lines = ["Today's schedule:"]
    for event in events:
        start = event.start.strftime("%H:%M")
        end = event.end.strftime("%H:%M")
        location = f" @ {event.location}" if event.location else ""
        lines.append(f"  {start}–{end}  {event.title}{location}")
    return "\n".join(lines)


def format_advice(advice_list: List[Advice]) -> str:
    """Render a list of Advice items as a multi-line string for CLI output.

    Warnings are prefixed with [!], info items with [i].
    """
    if not advice_list:
        return "[i] No advice — everything looks fine."
    lines = []
    for item in advice_list:
        prefix = _SEVERITY_PREFIX.get(item.severity, "[?]")
        lines.append(f"{prefix} {item.message}")
    return "\n".join(lines)


def format_error(message: str) -> str:
    """Render a plain-English error message for CLI output."""
    return f"[!] {message}"
