from dataclasses import dataclass
from typing import Literal, Optional


@dataclass
class Advice:
    """A single piece of advice produced by the rule engine, per PRD §5.3."""

    severity: Literal["info", "warning"]
    message: str                        # <= ~160 chars
    related_event: Optional[str] = None # event title, or None for general advice
