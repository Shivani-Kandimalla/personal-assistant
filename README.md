# Personal Assistant CLI

A terminal-based (REPL) personal assistant that fetches live weather, reads a
local schedule, and synthesises actionable daily advice — all with no API key
required.

```
> advice
[!] Morning Run: rain likely during your event. Consider rescheduling or bring rain gear.
[i] Client Lunch: temperatures reach 32°C+. Stay hydrated and wear sun protection.
[i] No tight transitions detected.
```

---

## Quick Start

```bash
# 1. Clone and enter the repo
cd personal-assistant

# 2. Install dependencies and the package
pip install -r requirements.txt
pip install -e .

# 3. Run
python -m assistant.main
```

No `.env` file or API key needed. Everything works out of the box.

---

## Commands

| Command | What it does |
|---|---|
| `weather <city>` | Current temperature + 12-hour forecast |
| `schedule` | Today's events from `calendar.json`, sorted by start time |
| `advice` | Full pipeline: weather + schedule → rule-based recommendations |
| `help` | List available commands |
| `exit` / `quit` | Leave the REPL |

**City name tips:** Plain city names work best (`London`, `Austin`, `Tokyo`).
State/country suffixes like `, TX` are stripped automatically. The output
always shows the fully resolved city name (e.g. `Austin, Texas, United States`)
so you can confirm the right place was matched.

---

## Optional Configuration

All settings have sensible defaults. Override via environment variables:

```bash
export DEFAULT_CITY="Austin"
export CALENDAR_PATH="./calendar.json"
export WEATHER_API_TIMEOUT_SECONDS=10
python -m assistant.main
```

---

## Project Structure

```
personal-assistant/
├── specs/PRD.md             # Source of truth — requirements, rules, data contracts
├── docs/rules.md            # AI persona + coding-agent constraints
├── calendar.json            # Your local schedule (edit this with your events)
├── requirements.txt         # Runtime + test dependencies
├── pyproject.toml           # Package config (src layout, pip install -e .)
└── src/assistant/
    ├── config/              # Settings loaded from env vars with defaults
    ├── calendar/            # JSON loading, schema validation, event querying
    ├── weather/             # Open-Meteo geocoding + forecast client + normaliser
    ├── advisor/             # Pure rule engine: WeatherReport + Events → Advice
    ├── cli/                 # REPL loop, command dispatch, output formatting
    └── main.py              # Thin composition root — wires everything together
```

Each module is independently unit-testable. `advisor/` is kept strictly pure
(no I/O, no network) so all six rules can be tested with plain data fixtures.

---

## Advice Rules (v1)

| # | Condition | Advice |
|---|---|---|
| R1 | Outdoor event + precipitation ≥ 50% during window | Warning: rain gear / reschedule |
| R2 | Outdoor event + wind ≥ 30 km/h during window | Warning: high wind caution |
| R3 | Event before 9 AM + temp ≤ 10°C | Info: layer up |
| R4 | Any event + temp ≥ 32°C | Info: hydration / sun protection |
| R5 | Consecutive events gap < 30 min, different locations | Warning: travel time conflict |
| R6 | No events today | Info: general forecast summary |

Rules are independent functions combined by a small orchestrator — not one
large if/elif block — so each is individually testable.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

87 tests covering every rule (fires + does-not-fire cases), every error path
(missing file, bad JSON, network timeout, unknown city), and the full REPL
command dispatch — zero live network calls in the test suite.

---

## Weather Data Source

**Open-Meteo** (https://open-meteo.com) — chosen deliberately because it
requires **no API key**, removing setup friction for anyone running the project.

Pipeline: `geocode city → lat/lon` → `fetch forecast → normalize → WeatherReport`

---

## Vibe Report

### Where did the AI's "vibe" drift?

**Scope creep on features.** During the `weather/` module build the AI
pre-emptively added more WMO weather codes and condition labels than the PRD
required. While harmless in isolation, this is exactly the pattern
`docs/rules.md` guards against — *"Don't add features, fields, or rules that
aren't in specs/PRD.md."* A single redirect ("follow the PRD scope") stopped
it, but only because the rule was written down explicitly.

**Premature downstream thinking.** When building `cli/`, the AI started
proposing a `--city` flag and a config-file loader — both v2 stretch goals
that weren't requested. The rule *"build one module at a time, in the order I
request"* was the guardrail that kept it on track. Without `docs/rules.md`
in scope, the agent would have quietly over-built.

### When did you have to use the "Builder Hammer"?

Three bugs surfaced during real testing — none caught by the unit tests alone:

1. **The geocoding suffix bug** — `weather Austin, TX` returned
   *"Unknown city 'Austin, TX'"* because Open-Meteo's geocoding API rejects
   state abbreviations after a comma. The AI built the geocode call correctly
   per spec, but the spec hadn't anticipated this real-world API constraint.
   A manual test exposed it; the architectural fix (`_strip_region_suffix()` +
   returning a resolved label like `"Austin, Texas, United States"`) was then
   directed back to the agent.

2. **The import path bug** — All source files used `from src.assistant.xxx
   import ...` which worked for pytest (pytest adds cwd to `sys.path`) but
   broke `python -m assistant.main` with `ModuleNotFoundError`. Adding
   `pyproject.toml` with the `src` layout and migrating all imports was a
   structural fix that required explicit architectural direction — the agent
   would not have caught this without a live end-to-end test.

3. **The slot-matching bug** — `advice` produced no output even with today's
   events and live weather. The root cause: Open-Meteo slots land on the hour
   (`16:00`, `17:00`), but the Afternoon Walk runs `16:30–17:00`. The original
   containment logic (`event.start <= slot_time < event.end`) excluded both
   slots — `16:00` is before 16:30, `17:00` is not before 17:00. The fix was
   changing to overlap logic: a slot at `T` covers `[T, T+1h)` and matches if
   it intersects the event window. This bug was invisible to all 87 unit tests
   because the test fixtures used events aligned to slot boundaries.

### What was your most successful "steering" prompt?

> *"Please read `specs/PRD.md` and `docs/rules.md` fully before doing
> anything. Once you have read both files, confirm you understand the
> architecture in PRD section 7 and the constraints in rules.md by restating
> them back to me in your own words. Do not write any code yet."*

Forcing the agent to **restate the architecture and constraints before writing
a single line of code** was the highest-leverage prompt of the session. It
established a shared mental model upfront and meant every subsequent module
was built against a verified understanding — not an assumed one.

### What context management looked like in practice

Context management was applied at two levels:

- **Session-level:** The PRD and rules were loaded at the start and kept in
  scope throughout. Every time a new module was started, the agent was asked
  to restate what it was about to build in 2–3 bullets before touching any
  file. This caught misalignments before they became code.

- **Module-level:** The bottom-up build order (`config → calendar → weather →
  advisor → cli → main`) meant each module was validated with tests before
  being used as a dependency. Bugs never compounded across layers.

The key insight: **the PRD and rules.md are not documentation — they are
active steering instruments.** Re-reading them before each module kept the
agent from drifting, and updating them after each real bug was found
permanently improved the spec for any future AI working on this codebase.
