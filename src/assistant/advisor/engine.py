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
from assistant.calendar.models import Event
from assistant.weather.models import WeatherReport

_RULES = [
    rule_r1_rain,
    rule_r2_wind,
    rule_r3_cold_morning,
    rule_r4_heat,
    rule_r5_tight_transition,
    rule_r6_no_events,
]


def run_advisor(report: WeatherReport, events: List[Event]) -> List[Advice]:
    """Run all advice rules and return the combined list of Advice items.

    Pure function: no I/O, no network, no printing.
    """
    results: List[Advice] = []
    for rule in _RULES:
        results.extend(rule(events, report))
    return results
