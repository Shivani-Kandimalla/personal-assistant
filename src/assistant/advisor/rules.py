from datetime import datetime
from typing import List, Optional

from assistant.advisor.models import Advice
from assistant.calendar.models import Event
from assistant.weather.models import HourlySlot, WeatherReport

OUTDOOR_KEYWORDS = {
    "run", "hike", "walk", "picnic", "outdoor", "park", "bike", "tennis", "golf"
}


def _is_outdoor(event: Event) -> bool:
    """Return True if the event title or location contains an outdoor keyword."""
    text = f"{event.title} {event.location}".lower()
    return any(kw in text for kw in OUTDOOR_KEYWORDS)


def _slots_for_event(event: Event, hourly: List[HourlySlot]) -> List[HourlySlot]:
    """Return hourly slots that overlap with [event.start, event.end).

    Each slot at time T represents conditions for the full hour [T, T+1h).
    A slot overlaps the event if the slot's hour-window intersects the event
    window — this handles events that start mid-hour (e.g. 16:30–17:00 is
    covered by the 16:00 slot, which runs 16:00–17:00).
    """
    from datetime import timedelta
    slots = []
    for slot in hourly:
        try:
            slot_time = datetime.fromisoformat(slot.time)
        except ValueError:
            continue
        slot_end = slot_time + timedelta(hours=1)
        if slot_time < event.end and slot_end > event.start:
            slots.append(slot)
    return slots


def rule_r1_rain(events: List[Event], report: WeatherReport) -> List[Advice]:
    """R1: outdoor event + precipitation_probability >= 50 → rain warning."""
    advice = []
    for event in events:
        if not _is_outdoor(event):
            continue
        slots = _slots_for_event(event, report.hourly)
        if any(s.precipitation_probability >= 50 for s in slots):
            advice.append(Advice(
                severity="warning",
                related_event=event.title,
                message=(
                    f"{event.title}: rain likely during your event. "
                    "Consider rescheduling or bring rain gear."
                ),
            ))
    return advice


def rule_r2_wind(events: List[Event], report: WeatherReport) -> List[Advice]:
    """R2: outdoor event + wind_speed_kmh >= 30 → high-wind warning."""
    advice = []
    for event in events:
        if not _is_outdoor(event):
            continue
        slots = _slots_for_event(event, report.hourly)
        if any(s.wind_speed_kmh >= 30 for s in slots):
            advice.append(Advice(
                severity="warning",
                related_event=event.title,
                message=(
                    f"{event.title}: high winds expected. "
                    "Use caution and secure any loose items."
                ),
            ))
    return advice


def rule_r3_cold_morning(events: List[Event], report: WeatherReport) -> List[Advice]:
    """R3: event before 9 AM + temp_c <= 10 → dress-warm info."""
    advice = []
    for event in events:
        if event.start.hour >= 9:
            continue
        slots = _slots_for_event(event, report.hourly)
        if any(s.temp_c <= 10 for s in slots):
            advice.append(Advice(
                severity="info",
                related_event=event.title,
                message=(
                    f"{event.title}: it'll be cold (≤10°C). "
                    "Layer up before heading out."
                ),
            ))
    return advice


def rule_r4_heat(events: List[Event], report: WeatherReport) -> List[Advice]:
    """R4: event + temp_c >= 32 → hydration/sun-protection info."""
    advice = []
    for event in events:
        slots = _slots_for_event(event, report.hourly)
        if any(s.temp_c >= 32 for s in slots):
            advice.append(Advice(
                severity="info",
                related_event=event.title,
                message=(
                    f"{event.title}: temperatures reach 32°C+. "
                    "Stay hydrated and wear sun protection."
                ),
            ))
    return advice


def rule_r5_tight_transition(events: List[Event], report: WeatherReport) -> List[Advice]:
    """R5: consecutive events with gap < 30 min and different locations → travel warning."""
    advice = []
    sorted_events = sorted(events, key=lambda e: e.start)
    for i in range(len(sorted_events) - 1):
        a, b = sorted_events[i], sorted_events[i + 1]
        gap_minutes = (b.start - a.end).total_seconds() / 60
        if gap_minutes < 30 and a.location.strip() != b.location.strip():
            advice.append(Advice(
                severity="warning",
                related_event=b.title,
                message=(
                    f"Tight gap between '{a.title}' and '{b.title}' "
                    f"({int(gap_minutes)} min, different locations). "
                    "Allow travel time."
                ),
            ))
    return advice


def rule_r6_no_events(events: List[Event], report: WeatherReport) -> List[Advice]:
    """R6: no events today → friendly general forecast info."""
    if events:
        return []
    condition = report.hourly[0].condition if report.hourly else "conditions unknown"
    temp = report.current_temp_c
    return [Advice(
        severity="info",
        related_event=None,
        message=(
            f"No events today. Current temp: {temp:.1f}°C, {condition}. "
            "A free day — enjoy it!"
        ),
    )]
