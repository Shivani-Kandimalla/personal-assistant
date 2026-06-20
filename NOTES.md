# Build Notes (working log — turn this into the Vibe Report later)

Keep entries short. Add one every time something interesting happens —
good or bad. This file is the raw material for the Vibe Report; you'll
summarize/curate it into the README at the end, not submit it as-is.

Format:
```
### [module/file] — one-line title
**What happened:**
**Drift, hammer, or good steer?**
**What I did about it:**
```

---

### Example entry (delete once you have real ones)
### advisor/rules.py — added an unrequested "sunscreen" rule
**What happened:** Cursor added a rule suggesting sunscreen for any outdoor
event regardless of temperature, which isn't in PRD §6.
**Drift, hammer, or good steer?** Vibe drift — scope creep beyond spec.
**What I did about it:** Pointed it at PRD §6 rules table, asked it to
remove anything not in R1–R6, re-reviewed the diff.
