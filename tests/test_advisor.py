import pytest
from datetime import datetime
from typing import List

from assistant.advisor.models import Advice
from assistant.advisor.rules import (
    rule_r1_rain,
    rule_r2_wind,
    rule_r3_cold_morning,
    rule_r4_heat,
    rule_r5_tight_transition,
    rule_r6_no_events,
)
from assistant.advisor.engine import run_advisor
from assistant.calendar.models import Event
from assistant.weather.models import HourlySlot, WeatherReport


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def make_event(
    title: str,
    start: str,
    end: str,
    location: str = "Office",
) -> Event:
    return Event(
        title=title,
        start=datetime.fromisoformat(start),
        end=datetime.fromisoformat(end),
        location=location,
    )


def make_slot(
    time: str,
    temp_c: float = 20.0,
    precip: int = 0,
    wind: float = 10.0,
    condition: str = "Clear",
) -> HourlySlot:
    return HourlySlot(
        time=time,
        temp_c=temp_c,
        precipitation_probability=precip,
        wind_speed_kmh=wind,
        condition=condition,
    )


def make_report(slots: List[HourlySlot], current_temp: float = 20.0) -> WeatherReport:
    return WeatherReport(
        city="TestCity",
        latitude=0.0,
        longitude=0.0,
        current_temp_c=current_temp,
        hourly=slots,
    )


# ---------------------------------------------------------------------------
# R1 — Rain warning for outdoor events
# ---------------------------------------------------------------------------

class TestR1Rain:
    def test_fires_for_outdoor_event_with_high_precip(self):
        event = make_event("Morning Run", "2026-06-18T07:00:00", "2026-06-18T07:45:00", "Riverside Park")
        report = make_report([make_slot("2026-06-18T07:00", precip=60)])
        advice = rule_r1_rain([event], report)
        assert len(advice) == 1
        assert advice[0].severity == "warning"
        assert advice[0].related_event == "Morning Run"
        assert "rain" in advice[0].message.lower()

    def test_does_not_fire_below_threshold(self):
        event = make_event("Morning Run", "2026-06-18T07:00:00", "2026-06-18T07:45:00", "Riverside Park")
        report = make_report([make_slot("2026-06-18T07:00", precip=40)])
        assert rule_r1_rain([event], report) == []

    def test_does_not_fire_for_indoor_event(self):
        event = make_event("Team Standup", "2026-06-18T09:00:00", "2026-06-18T09:15:00", "Office")
        report = make_report([make_slot("2026-06-18T09:00", precip=80)])
        assert rule_r1_rain([event], report) == []

    def test_fires_on_keyword_in_location(self):
        event = make_event("Lunch", "2026-06-18T12:00:00", "2026-06-18T13:00:00", "Central Park")
        report = make_report([make_slot("2026-06-18T12:00", precip=75)])
        advice = rule_r1_rain([event], report)
        assert len(advice) == 1


# ---------------------------------------------------------------------------
# R2 — High wind warning for outdoor events
# ---------------------------------------------------------------------------

class TestR2Wind:
    def test_fires_for_outdoor_event_with_high_wind(self):
        event = make_event("Afternoon Walk", "2026-06-18T16:00:00", "2026-06-18T17:00:00", "Greenbelt Trail")
        report = make_report([make_slot("2026-06-18T16:00", wind=35.0)])
        advice = rule_r2_wind([event], report)
        assert len(advice) == 1
        assert advice[0].severity == "warning"
        assert "wind" in advice[0].message.lower()

    def test_does_not_fire_below_threshold(self):
        event = make_event("Afternoon Walk", "2026-06-18T16:00:00", "2026-06-18T17:00:00", "Greenbelt Trail")
        report = make_report([make_slot("2026-06-18T16:00", wind=25.0)])
        assert rule_r2_wind([event], report) == []

    def test_does_not_fire_for_indoor_event(self):
        event = make_event("Meeting", "2026-06-18T10:00:00", "2026-06-18T11:00:00", "Conference Room")
        report = make_report([make_slot("2026-06-18T10:00", wind=50.0)])
        assert rule_r2_wind([event], report) == []


# ---------------------------------------------------------------------------
# R3 — Cold morning warning
# ---------------------------------------------------------------------------

class TestR3ColdMorning:
    def test_fires_for_early_event_with_low_temp(self):
        event = make_event("Early Meeting", "2026-06-18T07:00:00", "2026-06-18T08:00:00")
        report = make_report([make_slot("2026-06-18T07:00", temp_c=8.0)])
        advice = rule_r3_cold_morning([event], report)
        assert len(advice) == 1
        assert advice[0].severity == "info"
        assert "cold" in advice[0].message.lower() or "layer" in advice[0].message.lower()

    def test_does_not_fire_at_or_after_9am(self):
        event = make_event("Late Meeting", "2026-06-18T09:00:00", "2026-06-18T10:00:00")
        report = make_report([make_slot("2026-06-18T09:00", temp_c=5.0)])
        assert rule_r3_cold_morning([event], report) == []

    def test_does_not_fire_above_temp_threshold(self):
        event = make_event("Early Meeting", "2026-06-18T07:00:00", "2026-06-18T08:00:00")
        report = make_report([make_slot("2026-06-18T07:00", temp_c=15.0)])
        assert rule_r3_cold_morning([event], report) == []


# ---------------------------------------------------------------------------
# R4 — Heat warning
# ---------------------------------------------------------------------------

class TestR4Heat:
    def test_fires_when_temp_at_or_above_32(self):
        event = make_event("Client Lunch", "2026-06-18T12:00:00", "2026-06-18T13:00:00")
        report = make_report([make_slot("2026-06-18T12:00", temp_c=34.0)])
        advice = rule_r4_heat([event], report)
        assert len(advice) == 1
        assert advice[0].severity == "info"
        assert "hydrat" in advice[0].message.lower() or "sun" in advice[0].message.lower()

    def test_does_not_fire_below_threshold(self):
        event = make_event("Client Lunch", "2026-06-18T12:00:00", "2026-06-18T13:00:00")
        report = make_report([make_slot("2026-06-18T12:00", temp_c=28.0)])
        assert rule_r4_heat([event], report) == []

    def test_fires_for_any_event_type(self):
        event = make_event("Indoor Meeting", "2026-06-18T14:00:00", "2026-06-18T15:00:00", "Office")
        report = make_report([make_slot("2026-06-18T14:00", temp_c=33.0)])
        advice = rule_r4_heat([event], report)
        assert len(advice) == 1


# ---------------------------------------------------------------------------
# R5 — Tight transition warning
# ---------------------------------------------------------------------------

class TestR5TightTransition:
    def test_fires_for_consecutive_events_short_gap_different_locations(self):
        a = make_event("Standup", "2026-06-18T09:00:00", "2026-06-18T09:15:00", "Office")
        b = make_event("Client Lunch", "2026-06-18T09:30:00", "2026-06-18T10:30:00", "Downtown Bistro")
        report = make_report([])
        advice = rule_r5_tight_transition([a, b], report)
        assert len(advice) == 1
        assert advice[0].severity == "warning"
        assert "travel" in advice[0].message.lower() or "gap" in advice[0].message.lower()

    def test_does_not_fire_when_gap_is_30_minutes_or_more(self):
        a = make_event("Standup", "2026-06-18T09:00:00", "2026-06-18T09:15:00", "Office")
        b = make_event("Client Lunch", "2026-06-18T09:45:00", "2026-06-18T10:45:00", "Downtown Bistro")
        report = make_report([])
        assert rule_r5_tight_transition([a, b], report) == []

    def test_does_not_fire_when_same_location(self):
        a = make_event("Meeting 1", "2026-06-18T09:00:00", "2026-06-18T09:15:00", "Office")
        b = make_event("Meeting 2", "2026-06-18T09:20:00", "2026-06-18T09:45:00", "Office")
        report = make_report([])
        assert rule_r5_tight_transition([a, b], report) == []

    def test_does_not_fire_for_single_event(self):
        a = make_event("Solo", "2026-06-18T09:00:00", "2026-06-18T10:00:00", "Office")
        report = make_report([])
        assert rule_r5_tight_transition([a], report) == []


# ---------------------------------------------------------------------------
# R6 — No events fallback
# ---------------------------------------------------------------------------

class TestR6NoEvents:
    def test_fires_when_no_events(self):
        report = make_report([make_slot("2026-06-18T08:00", temp_c=22.0, condition="Clear")], current_temp=22.0)
        advice = rule_r6_no_events([], report)
        assert len(advice) == 1
        assert advice[0].severity == "info"
        assert advice[0].related_event is None
        assert "no events" in advice[0].message.lower()

    def test_does_not_fire_when_events_exist(self):
        event = make_event("Morning Run", "2026-06-18T07:00:00", "2026-06-18T08:00:00")
        report = make_report([])
        assert rule_r6_no_events([event], report) == []


# ---------------------------------------------------------------------------
# run_advisor orchestrator
# ---------------------------------------------------------------------------

class TestRunAdvisor:
    def test_returns_list_of_advice(self):
        event = make_event("Morning Run", "2026-06-18T07:00:00", "2026-06-18T07:45:00", "Riverside Park")
        report = make_report([make_slot("2026-06-18T07:00", precip=70, temp_c=8.0)])
        results = run_advisor(report, [event])
        assert isinstance(results, list)
        assert all(isinstance(a, Advice) for a in results)

    def test_r6_fires_via_orchestrator_when_no_events(self):
        report = make_report([make_slot("2026-06-18T08:00")], current_temp=20.0)
        results = run_advisor(report, [])
        assert any("no events" in a.message.lower() for a in results)

    def test_warning_for_outdoor_rainy_event(self):
        event = make_event("Hike", "2026-06-18T10:00:00", "2026-06-18T12:00:00", "Mountain Trail")
        report = make_report([make_slot("2026-06-18T10:00", precip=80)])
        results = run_advisor(report, [event])
        warnings = [a for a in results if a.severity == "warning"]
        assert len(warnings) >= 1
        assert any("rain" in a.message.lower() for a in warnings)
