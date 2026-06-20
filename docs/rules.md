# Rules & Constraints

This file has two audiences and both matter:
1. **The assistant's voice** — how the CLI should *sound* to the end user.
2. **The coding agent's behavior** — how Cursor must build and modify this
   codebase. Re-paste this file into Cursor any time output drifts from it.

---

## Part A — Assistant Persona (how the app talks to the user)

- **Tone:** concise, warm, practical. Like a competent assistant, not a
  chatbot trying to be your friend.
- **Length:** each advice message is one or two short sentences, under
  ~160 characters. No filler ("I hope this helps!", "Great question!").
- **No emoji, no exclamation-mark stacking.** One exclamation mark max, and
  only if genuinely warranted (e.g. a real warning).
- **No invented facts.** If weather data or calendar data is missing/partial,
  say so plainly rather than guessing or filling gaps with generic advice.
- **Severity is visible:** `warning` items should be visually distinguished
  from `info` items in CLI output (e.g. a prefix like `[!]` vs `[i]`), not
  just internally tagged and then displayed identically.
- **Errors talk to humans, not stack traces.** Any caught exception prints a
  one-line, plain-English explanation of what went wrong and what the user
  can do next (e.g. "Couldn't reach the weather service — check your
  internet connection and try again.").
- **Resolved city label:** the `weather` and `advice` output must show the
  fully qualified city name returned by the geocoding API (e.g.
  `"Austin, Texas, United States"`), not the raw string the user typed.
  This prevents silent wrong-city matches and requires no extra input.
- **Output format is fixed — do not deviate:**
  - `[!]` is the exact prefix for every `warning` advice item and every error message.
  - `[i]` is the exact prefix for every `info` advice item.
  - No emoji, no `WARNING:`, no `⚠️`, no colour codes unless explicitly requested.
  - Refer to the sample session in `specs/PRD.md` §3 as the canonical reference.

## Part B — Constraints on the Coding Agent (Cursor)

These are non-negotiable unless I explicitly say otherwise in chat.

### Structure & size
- Follow the folder structure in `specs/PRD.md` §7 exactly. Don't introduce
  new top-level packages or rename modules without asking first.
- A `pyproject.toml` is required for the `src` layout. Use exactly this
  build configuration (do not substitute a different backend or layout):
  ```toml
  [build-system]
  requires = ["setuptools>=68"]
  build-backend = "setuptools.build_meta"

  [tool.setuptools.packages.find]
  where = ["src"]
  ```
  Run `pip install -e .` once after project setup. Without it,
  `python -m assistant.main` fails with `ModuleNotFoundError`.
- Do not move source files out of `src/`. All internal imports must use
  `from assistant.xxx import ...` — never `from src.assistant.xxx import ...`.
- Monkeypatching in tests must use `patch("assistant.module.symbol")` —
  not `patch("src.assistant.module.symbol")`. Using the wrong path causes
  the patch to silently not apply and tests to pass for the wrong reason.
- Keep files small: target under ~150 lines each. If a function exceeds
  ~40 lines, propose a split instead of letting it grow.
- `advisor/` must stay pure: no `print()`, no `requests`/`httpx` calls, no
  file I/O inside it. It only takes data in and returns data out.
- `main.py` is composition only — it wires modules together. No business
  logic lives there.

### Configuration & location
- The user's city is controlled by the `DEFAULT_CITY` environment variable.
  The hardcoded fallback in `settings.py` is `"Katy"`. Do not hardcode any
  other city unless the user explicitly asks.
- Do not add IP-based or GPS-based location detection unless the user
  explicitly requests it (v2 stretch goal).
- `calendar.json` event dates must match today's local date for `schedule`
  and `advice` to return results. This is a known operational constraint,
  not a bug. Document it; do not silently auto-roll dates unless asked.
- **Critical for any AI reproducing this project:** when generating or
  editing `calendar.json`, always use the actual current date — never copy
  the example date from the PRD verbatim. A stale date causes `get_today_events()`
  to return an empty list, so no advice rules fire and only R6 triggers.

### Geocoding behaviour
- Before sending a city name to the Open-Meteo Geocoding API, strip
  everything after the first comma (`"Austin, TX"` → `"Austin"`). The API
  does not accept state or country suffixes.
- Always use the fully resolved label from the geocoding response (`name`,
  `admin1`, `country`) as `WeatherReport.city`. Never store the raw user
  input string as the city.

### Slot-matching behaviour
- Each Open-Meteo hourly slot at time `T` covers the full hour `[T, T+1h)`.
  A slot overlaps an event if `slot_time < event.end AND slot_time + 1h >
  event.start`. Do not use strict containment (`event.start <= slot_time <
  event.end`) — it silently drops mid-hour events.

### Process
- Build one module at a time, in the order I request. Don't pre-build
  downstream modules "while you're at it."
- Before writing code for a new module, briefly restate (2-3 bullets) what
  you're about to build and why, so I can correct course before you write.
- After finishing a module, summarize what you built in 3 bullets max.
- Don't add new dependencies to `requirements.txt` without asking me first
  and explaining why the standard library or existing deps aren't enough.
- Don't add features, fields, or rules that aren't in `specs/PRD.md`. If you
  think something's missing, ask — don't silently add it.

### Code quality
- Use type hints on all function signatures (Python).
- Every public function/class gets a short docstring.
- Don't swallow exceptions with a bare `except:`. Catch specific exceptions,
  log or message clearly, and either re-raise as a typed error or return a
  clearly-typed failure value — never fail silently.
- No network calls inside test files. Weather API calls must be mockable
  (inject a client/session or use a thin wrapper function that tests can
  monkeypatch). Use `patch("assistant.module.name", ...)` — not
  `patch("src.assistant.module.name", ...)` — to match the installed import
  path.
- Every new module gets at least a basic test in `tests/` in the same PR/
  step — not deferred to "later."

### When I push back
- If I say "re-check `docs/rules.md`," stop and diff your last change
  against this file specifically before responding.
- If I say "explain this back to me," answer in plain language before
  touching any more code.
