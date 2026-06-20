import json
from datetime import datetime, date
from pathlib import Path
from typing import List

from .models import Event


class CalendarError(Exception):
    """Raised when the calendar file cannot be loaded or parsed."""


def _parse_event(raw: object, index: int) -> Event:
    """Parse a single raw dict into an Event; raise CalendarError on bad data."""
    if not isinstance(raw, dict):
        raise CalendarError(f"Event #{index} is not an object.")

    missing = [f for f in ("title", "start", "end", "location") if f not in raw]
    if missing:
        raise CalendarError(
            f"Event #{index} is missing required field(s): {', '.join(missing)}."
        )

    try:
        start = datetime.fromisoformat(raw["start"])
        end = datetime.fromisoformat(raw["end"])
    except ValueError as exc:
        raise CalendarError(
            f"Event #{index} has an invalid datetime: {exc}"
        ) from exc

    return Event(
        title=str(raw["title"]),
        start=start,
        end=end,
        location=str(raw["location"]),
        notes=str(raw.get("notes", "")),
    )


def load_events(calendar_path: str) -> List[Event]:
    """Load and validate all events from the calendar JSON file.

    Returns an empty list when the file exists but has no events.
    Raises CalendarError for missing file, bad JSON, or schema violations.
    """
    path = Path(calendar_path)

    if not path.exists():
        raise CalendarError(
            f"Calendar file not found: {calendar_path}. "
            "Check your CALENDAR_PATH setting."
        )

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise CalendarError(f"Could not read calendar file: {exc}") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise CalendarError(
            f"calendar.json contains invalid JSON: {exc}"
        ) from exc

    if not isinstance(data, dict) or "events" not in data:
        raise CalendarError(
            "calendar.json must be an object with an \"events\" array."
        )

    raw_events = data["events"]
    if not isinstance(raw_events, list):
        raise CalendarError("The \"events\" field must be an array.")

    return [_parse_event(item, i + 1) for i, item in enumerate(raw_events)]


def get_today_events(calendar_path: str, today: date | None = None) -> List[Event]:
    """Return events for today, sorted by start time.

    Uses the current local date when *today* is not supplied.
    Propagates CalendarError from load_events unchanged.
    """
    target = today or date.today()
    events = load_events(calendar_path)
    todays = [e for e in events if e.start.date() == target]
    return sorted(todays, key=lambda e: e.start)
