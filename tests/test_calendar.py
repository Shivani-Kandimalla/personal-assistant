import json
import pytest
from datetime import date, datetime
from pathlib import Path

from assistant.calendar.loader import load_events, get_today_events, CalendarError
from assistant.calendar.models import Event


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_calendar(tmp_path: Path, data: object) -> str:
    """Write *data* as JSON to a temp file and return its path string."""
    p = tmp_path / "calendar.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


VALID_DATA = {
    "events": [
        {
            "title": "Morning Run",
            "start": "2026-06-18T07:00:00",
            "end": "2026-06-18T07:45:00",
            "location": "Riverside Park",
        },
        {
            "title": "Team Standup",
            "start": "2026-06-18T09:00:00",
            "end": "2026-06-18T09:15:00",
            "location": "Office",
        },
    ]
}


# ---------------------------------------------------------------------------
# load_events
# ---------------------------------------------------------------------------

class TestLoadEvents:
    def test_valid_calendar_returns_events(self, tmp_path):
        path = write_calendar(tmp_path, VALID_DATA)
        events = load_events(path)
        assert len(events) == 2
        assert events[0].title == "Morning Run"
        assert isinstance(events[0].start, datetime)

    def test_empty_events_list_returns_empty(self, tmp_path):
        path = write_calendar(tmp_path, {"events": []})
        assert load_events(path) == []

    def test_missing_file_raises_calendar_error(self, tmp_path):
        with pytest.raises(CalendarError, match="not found"):
            load_events(str(tmp_path / "nonexistent.json"))

    def test_malformed_json_raises_calendar_error(self, tmp_path):
        p = tmp_path / "calendar.json"
        p.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(CalendarError, match="invalid JSON"):
            load_events(str(p))

    def test_missing_events_key_raises_calendar_error(self, tmp_path):
        path = write_calendar(tmp_path, {"data": []})
        with pytest.raises(CalendarError, match='"events"'):
            load_events(path)

    def test_event_missing_required_field_raises_calendar_error(self, tmp_path):
        data = {"events": [{"title": "Run", "start": "2026-06-18T07:00:00"}]}
        path = write_calendar(tmp_path, data)
        with pytest.raises(CalendarError, match="missing required field"):
            load_events(path)

    def test_event_invalid_datetime_raises_calendar_error(self, tmp_path):
        data = {
            "events": [
                {
                    "title": "Run",
                    "start": "not-a-date",
                    "end": "2026-06-18T07:45:00",
                    "location": "Park",
                }
            ]
        }
        path = write_calendar(tmp_path, data)
        with pytest.raises(CalendarError, match="invalid datetime"):
            load_events(path)

    def test_optional_notes_field_is_read(self, tmp_path):
        data = {
            "events": [
                {
                    "title": "Run",
                    "start": "2026-06-18T07:00:00",
                    "end": "2026-06-18T07:45:00",
                    "location": "Park",
                    "notes": "Bring water",
                }
            ]
        }
        path = write_calendar(tmp_path, data)
        events = load_events(path)
        assert events[0].notes == "Bring water"


# ---------------------------------------------------------------------------
# get_today_events
# ---------------------------------------------------------------------------

class TestGetTodayEvents:
    def test_returns_only_todays_events(self, tmp_path):
        data = {
            "events": [
                {
                    "title": "Today Event",
                    "start": "2026-06-18T08:00:00",
                    "end": "2026-06-18T09:00:00",
                    "location": "Here",
                },
                {
                    "title": "Tomorrow Event",
                    "start": "2026-06-19T08:00:00",
                    "end": "2026-06-19T09:00:00",
                    "location": "There",
                },
            ]
        }
        path = write_calendar(tmp_path, data)
        events = get_today_events(path, today=date(2026, 6, 18))
        assert len(events) == 1
        assert events[0].title == "Today Event"

    def test_events_sorted_by_start_time(self, tmp_path):
        data = {
            "events": [
                {
                    "title": "Late Event",
                    "start": "2026-06-18T14:00:00",
                    "end": "2026-06-18T15:00:00",
                    "location": "A",
                },
                {
                    "title": "Early Event",
                    "start": "2026-06-18T07:00:00",
                    "end": "2026-06-18T08:00:00",
                    "location": "B",
                },
            ]
        }
        path = write_calendar(tmp_path, data)
        events = get_today_events(path, today=date(2026, 6, 18))
        assert events[0].title == "Early Event"
        assert events[1].title == "Late Event"

    def test_no_events_today_returns_empty(self, tmp_path):
        path = write_calendar(tmp_path, {"events": []})
        events = get_today_events(path, today=date(2026, 6, 18))
        assert events == []
