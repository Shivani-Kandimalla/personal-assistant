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

## Part B — Constraints on the Coding Agent (Cursor)

These are non-negotiable unless I explicitly say otherwise in chat.

### Structure & size
- Follow the folder structure in `specs/PRD.md` §7 exactly. Don't introduce
  new top-level packages or rename modules without asking first.
- Keep files small: target under ~150 lines each. If a function exceeds
  ~40 lines, propose a split instead of letting it grow.
- `advisor/` must stay pure: no `print()`, no `requests`/`httpx` calls, no
  file I/O inside it. It only takes data in and returns data out.
- `main.py` is composition only — it wires modules together. No business
  logic lives there.

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
  monkeypatch).
- Every new module gets at least a basic test in `tests/` in the same PR/
  step — not deferred to "later."

### When I push back
- If I say "re-check `docs/rules.md`," stop and diff your last change
  against this file specifically before responding.
- If I say "explain this back to me," answer in plain language before
  touching any more code.
