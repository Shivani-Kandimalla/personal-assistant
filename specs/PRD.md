# PRD — Personal Assistant CLI

## 1. Problem Statement
Busy people context-switch between a weather app and a calendar app every
morning to decide how to plan their day. This tool merges both into a single
local CLI (REPL) that fetches live weather, reads a local schedule, and
synthesizes short, actionable advice — e.g. "Bring a jacket, your 9 AM
outdoor run starts at 52°F" or "Rain expected during your 2 PM walk —
consider moving it indoors."

## 2. Users & Context
Single-user, local, terminal-based. No auth, no multi-tenancy, no persistence
beyond the existing local `calendar.json` file. This is a personal tool, not
a SaaS product.

## 3. Core Features (must-have, v1 scope)

1. **REPL loop** — an interactive prompt that accepts commands repeatedly
   until the user exits. Required commands:
   - `weather <city>` — fetch and display current + short-term forecast
   - `schedule` — list today's events from `calendar.json`
   - `advice` — run the full pipeline (weather + schedule → advice) and
     print recommendations
   - `help` — list available commands
   - `exit` / `quit` — leave the REPL cleanly
2. **Weather data source** — **Open-Meteo** (https://open-meteo.com).
   Chosen deliberately because it requires **no API key**, which removes
   setup friction and a whole class of "works on my machine" failures for
   anyone reviewing this project. Flow: geocode a city name to lat/lon
   (Open-Meteo Geocoding API) → fetch forecast (Open-Meteo Forecast API) →
   normalize the response into an internal `WeatherReport` shape.
3. **Local schedule** — read and validate `calendar.json` (schema below).
   Must handle: missing file, malformed JSON, empty event list, and events
   missing required fields, all without crashing the REPL.
4. **Advice synthesis** — **rule-based for v1** (see §6 for the explicit
   rationale and the rules themselves). Pure function(s): takes a
   `WeatherReport` + a list of `Event`s → returns a list of `Advice` items.
   No hidden network calls inside this layer — it must be unit-testable
   with zero internet access.
5. **Error handling** — no internet / API timeout, malformed calendar file,
   unknown city, empty schedule. Every failure mode prints a clear message
   and returns to the REPL prompt; nothing should stack-trace to the user.

## 4. Non-Goals (explicitly out of scope for v1)
- No GUI / web frontend.
- No database; `calendar.json` is the only persistence.
- No multi-user accounts or authentication.
- No write-back to the calendar (read-only).
- No notifications/scheduling daemon — this is invoked manually per command.

## 5. Data Contracts

### 5.1 `calendar.json` schema (minimum)
```json
{
  "events": [
    {
      "title": "Morning Run",
      "start": "2026-06-18T07:00:00",
      "end": "2026-06-18T07:45:00",
      "location": "Riverside Park"
    }
  ]
}
```
- `start` / `end`: ISO 8601 local datetime strings.
- `location`: free text; may be empty string but key must be present.
- Additional optional fields (e.g. `notes`, `tags`) are allowed but not
  required for v1 logic.

### 5.2 Internal `WeatherReport` shape (post-normalization)
```python
{
  "city": str,
  "latitude": float,
  "longitude": float,
  "current_temp_c": float,
  "hourly": [
    {
      "time": "2026-06-18T07:00",
      "temp_c": float,
      "precipitation_probability": int,  # 0-100
      "wind_speed_kmh": float,
      "condition": str  # human-readable, e.g. "Rain", "Clear"
    },
    ...
  ]
}
```

### 5.3 Internal `Advice` shape
```python
{
  "severity": "info" | "warning",
  "related_event": str | None,   # event title, or None for general advice
  "message": str                  # <= ~160 chars, persona per docs/rules.md
}
```

## 6. Advice Synthesis — Design Decision & Rules

**Decision: rule-based, not LLM-powered, for v1.**
Rationale (document this — it's a graded design choice, not a default):
- Determinism: identical inputs must always produce identical advice, which
  makes the logic unit-testable without mocking an LLM.
- Zero added cost/dependency/API key for anyone running this project.
- The decision space here (weather × calendar overlap) is small and well
  enumerable — a rule engine is the right-sized tool, not under- or
  over-engineering.
- An LLM-powered "phrasing" layer is listed as a documented v2 stretch
  goal (see §8) — rules decide *whether/what* advice fires, an optional LLM
  could later only restyle the *wording*, never the underlying decision.

**v1 rules (the advisor module must implement at least these):**

| # | Condition | Advice |
|---|---|---|
| R1 | Event title/location contains an outdoor keyword (`run`, `hike`, `walk`, `picnic`, `outdoor`, `park`, `bike`, `tennis`, `golf`) AND forecast during event window shows `precipitation_probability >= 50` | Warning: suggest rescheduling or bringing rain gear |
| R2 | Same outdoor-keyword match AND `wind_speed_kmh >= 30` during window | Warning: high wind, advise caution / secure loose items |
| R3 | Event starts before 9:00 AM AND forecast `temp_c <= 10` during window | Info: suggest layering / warm clothing |
| R4 | Event starts AND forecast `temp_c >= 32` during window | Info: suggest hydration / sun protection |
| R5 | Two consecutive events have a gap < 30 minutes AND their `location` values differ | Warning: tight transition, flag possible travel time conflict |
| R6 | No events today | Info: friendly "no events, here's today's general forecast" message |

Rules should be implemented as independent, individually testable functions
combined by a small orchestrator — not one large if/elif block.

## 7. Architecture Intent
```
src/assistant/
├── cli/         REPL loop, command parsing/dispatch, output formatting
├── weather/     Open-Meteo client + response normalization
├── calendar/    JSON loading, schema validation, event querying helpers
├── advisor/     Rule engine: (WeatherReport, list[Event]) -> list[Advice]
├── config/      env/config loading (timeouts, default city, file paths)
└── main.py      thin composition root only — no business logic
```
Each module is independently unit-testable. `cli/` is the only layer allowed
to do I/O formatting (printing); `advisor/` must remain pure (no I/O, no
network, no printing) so it can be tested with plain fixtures.

## 8. Stretch Goals (v2, not required for grading but OK to mention)
- Optional LLM-powered rewrite of advice wording (rules still decide *what*
  fires; LLM only restyles *how* it's said) behind a `--llm` flag.
- Multi-day schedule lookahead instead of "today only."
- Config-driven outdoor-keyword list instead of hardcoded.

## 9. Acceptance Criteria (map directly to tests/)
- [ ] `schedule` command lists all events for today, sorted by start time.
- [ ] `weather <city>` prints current temp + next-12-hour summary; unknown
      city prints a clear error, not a crash.
- [ ] `advice` with an outdoor event + rainy forecast produces at least one
      `warning`-severity item mentioning rain/reschedule.
- [ ] `advice` with an empty `calendar.json` produces the R6 fallback message
      and does not error.
- [ ] Malformed `calendar.json` (invalid JSON) is caught with a clear error
      message; REPL remains usable afterward.
- [ ] All advisor rules (R1–R6) have at least one passing unit test with
      hand-constructed fixtures (no live network/API calls in tests).
- [ ] App runs end-to-end via `python -m assistant.main` with only
      `requirements.txt` installed and no API key required.
