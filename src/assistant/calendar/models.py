from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Event:
    """A single calendar event loaded from calendar.json."""

    title: str
    start: datetime
    end: datetime
    location: str
    notes: str = field(default="")
