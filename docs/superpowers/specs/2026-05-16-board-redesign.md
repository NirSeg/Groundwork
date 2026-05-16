# Board Redesign Spec

## Goal

Restructure the Groundwork board from a flat topic-folder layout into a hierarchical `issues/` system driven by `schedule.json` as the source of truth, with time-horizon priorities, bidirectional md↔json sync, CalDAV generation, and end-of-day overflow logic.

---

## Directory Structure

```
board/
├── p0.md              ← generated, today's schedule (chronological, aggregated)
├── p1.md              ← generated, this week (aggregated)
├── p2.md              ← flat list, manually maintained (aggregated)
├── done.md            ← daily review: last 3 days completions + graphs (generated, updated EOD)
├── schedule.json      ← merged from all issues (generated)
├── history.csv        ← all past tasks + events (merged, updated EOD)
├── SKILL.md
├── graphs/
└── issues/
    ├── shabits/           ← real directory, no p1/p2
    │   ├── p0.md
    │   ├── done.md
    │   ├── history.csv
    │   ├── schedule.json
    │   ├── SKILL.md
    │   └── graphs/
    ├── projects/          ← grouping folder only, no own files
    │   └── cv  →  ~/Projects/cv/.board/          ← symlink
    ├── reading-material/  ← grouping folder only
    │   ├── mvg     →  ~/Study/mvg/.board/     ← symlink
    │   ├── papers  →  ~/Study/papers/.board/  ← symlink
    │   └── rl      →  ~/Study/rl/.board/      ← symlink
    └── work/              ← grouping folder only
        └── ai_therapist  →  ~/Work/AI_Therapist/.board/  ← symlink
```

**Symlink rule:** every issue under a grouping folder is a symlink to `<anywhere>/<name>/.board/`. The `.board/` directory lives inside its project/course/work repo — it is not restricted to `~/Projects/`. Examples:

```
issues/work/ai_therapist        →  ~/Work/AI_Therapist/.board/
issues/projects/cv              →  ~/Projects/cv/.board/
issues/reading-material/mvg     →  ~/Book & Courses/mvg/.board/
```

Each `.board/` directory contains the full issue layout:

```
.board/
├── p0.md
├── p1.md
├── p2.md
├── done.md
├── history.csv
├── schedule.json
├── SKILL.md
└── graphs/
```

`shabits/` is the only real (non-symlinked) issue directory — it has no separate project repo.

Grouping folders (`projects/`, `reading-material/`, `work/`) are real directories containing only symlinks. All scripts use `find -L` / `followlinks=True` to traverse them.

---

## Mental Model

Three levels of work:
- **Goals** = Issues — what you're actively working on. Only active goals live in the board. A goal is added manually when you start working on it, typically when a previous goal wraps up.
- **Missions** = Events — a specific, time-bounded work session within a goal. SMART applies here first: a mission should have a clear outcome so you know when it's done.
- **Todos** = Tasks — SMART action items within a mission, sized to fit the time block.

Goals/Missions/Todos are the mental model. The files use p0/p1/p2, events, and tasks — no renaming in headers.

## Priority Lanes — Time Horizon

| Lane | Horizon | Decision rule |
|------|---------|---------------|
| p0 | Today | Has a time block scheduled for today |
| p1 | This week | Due or time-blocked within the current week |
| p2 | This month / coming months | Planned work, but not this week — may have due dates and time blocks |

The question that determines lane is **when**. p2 is not a vague backlog — missions there can have due dates and time blocks, they're just further out than this week. When a p2 mission moves into the current week it graduates to p1; when it gets a time block today it moves to p0.

---

## schedule.json Format (per issue)

`schedule.json` holds active events (p0, p1) plus a 3-day rolling window of completed events (`done`). The `done` section is the edit window for recent sessions — you can add or correct tasks there, and changes sync back to the corresponding VEVENT DESCRIPTION in CalDAV. After 3 days, events are pruned from `done` and live only in `history.csv`.

```json
{
  "issue": "cv",
  "p0": [
    {
      "id": "set-up-rocm-env",
      "title": "Set up ROCm environment",
      "date": "2026-05-16",
      "time_blocks": [["10:00", "12:00"]],
      "tasks": [
        {"id": "t1", "text": "Install ROCm drivers", "done": false},
        {"id": "t2", "text": "Configure PyTorch", "done": false}
      ]
    }
  ],
  "p1": [
    {
      "id": "implement-gaussians",
      "title": "Implement 3D Gaussian data structures",
      "due": "2026-05-20",
      "time_blocks": [["10:00", "12:00"]],
      "tasks": []
    }
  ],
  "done": [
    {
      "id": "debug-loader",
      "title": "Debug data loader",
      "date": "2026-05-14",
      "time_blocks": [["14:00", "16:00"]],
      "actual": ["14:05", "15:50"],
      "tasks": [
        {"id": "t1", "text": "Reproduce crash", "done": true},
        {"id": "t2", "text": "Fix off-by-one in batch index", "done": true}
      ]
    }
  ]
}
```

- `p0` events: require `date` + `time_blocks`
- `p1` events: optional `due` and/or `time_blocks`
- `p2`: not in schedule.json — lives only in p2.md
- `done`: last 3 days of completed events, pruned at EOD; edits here sync back to VEVENT DESCRIPTION in CalDAV
- `actual` field (optional, `done` events only): `["HH:MM", "HH:MM"]` actual start/end of the session — used for actual-vs-planned graphs. If absent, `time_blocks` is used as the estimate. **Deferred — fill in once the system is running and you decide you want it.**
- Recurring events (shabits): include `"recurring": {"days": ["Mon", ...]}` field; VEVENTs are generated fresh per day (no RRULE) so each occurrence can have its own DESCRIPTION

Board-level `schedule.json` is merged from all issues at aggregation time.

---

## p0.md Format

Events sorted chronologically by first time_block start. Events without time blocks go under `## Unscheduled` at the bottom.

Night routine shabits from the previous evening appear in a `## Shabits — Last Night` section at the top of the next morning's p0.md so they can be ticked off before starting the day. This keeps all actionable items in p0.md — done.md is purely retrospective.

```markdown
# CV — Fri 2026-05-16

## Shabits — Last Night
- [ ] Prepare for bed
- [ ] Evening Meditation
- [ ] Read before sleep

## Set up ROCm environment  10:00–12:00
- [ ] Install ROCm drivers
- [ ] Configure PyTorch

## Implement Gaussian renderer  14:00–16:00
- [ ] Write forward pass
- [ ] Add unit tests
```

Board-level `p0.md` groups by issue heading, same chronological ordering:

```markdown
# Board — Fri 2026-05-16

## Shabits
### Shabits — Last Night
- [ ] Prepare for bed
- [ ] Evening Meditation

### Morning habits  07:00–07:30
- [ ] Morning Routine
- [ ] Morning Meditation

## CV
### Set up ROCm environment  10:00–12:00
- [ ] Install ROCm drivers
```

## p1.md Format

```markdown
# CV — Week of 2026-05-16

## Implement 3D Gaussian data structures  (due: Wed, 10:00–12:00)
## Write training loop
## Scene densification and pruning  (due: Fri)
```

## p2.md Format

Flat list of event titles only — no dates, no tasks, no connection to schedule.json:

```markdown
# CV

## Deploy to staging
## User testing round 1
## Incremental pipeline
```

## done.md Format

Purely retrospective. Generated from `history.csv` and `shabits.csv`. Updated at end of day only. Night routine habits are reviewed in p0.md the next morning, not here.

Content per issue (last 3 days):
- Completed events with their tasks, grouped by date
- Actual vs planned time per event (where `actual` field is present)
- Completion graphs from `graphs/`

For shabits specifically:
- Shows which habits were missed in the last 3 days
- Missed habits that were actually done but not ticked off can be retroactively marked complete
- Any habit missed yesterday that cannot be confirmed done is flagged **"must complete today"**

---

## Bidirectional Sync

File watcher monitors all issue-level `p0.md`, `p1.md`, `done.md`, and `schedule.json` files, **and** the board-level `p0.md`, `p1.md`, `done.md`. Changes propagate in both directions between board-level and issue-level files.

### md → schedule.json (real-time)

| File | Change | Engine action |
|---|---|---|
| p0.md | `[x]` task checked | `done: true` in schedule.json p0 |
| p0.md | `[ ]` task checked in "Shabits — Last Night" | marks habit done in shabits schedule.json |
| p0.md | New `- [ ] text` line added | New task entry in event |
| p0.md | New `## Title  HH:MM–HH:MM` heading | New p0 event in schedule.json |
| p0.md | New `## Title  (due: ...)` heading | New p1 event in schedule.json |
| p0.md | Event title renamed | Update title in schedule.json |
| p1.md | New `## Title  (due: ...)` heading | New p1 event in schedule.json |
| done.md | `[x]` task checked | `done: true` in schedule.json `done` section |
| done.md | `[ ]` task unchecked | `done: false` in schedule.json `done` section |
| done.md | New `- [ ] text` line added | New task entry in `done` event |

### schedule.json → md (real-time)

| Change in schedule.json | Engine action |
|---|---|
| Event added/edited in p0/p1 | Regenerate relevant md file |
| Task marked done in p0 | Check off `[x]` in p0.md |
| Event moved from p0 to done | Remove from p0.md; add to done.md |
| Event removed | Remove from md |
| Task edited in done section | Update done.md |

### Board ↔ Issue bidirectional sync

The board-level md files are aggregated views, but edits in them propagate back to the source issue:

| Change in board-level md | Engine action |
|---|---|
| Task ticked in `board/p0.md` | Find source issue, update issue-level schedule.json |
| Task ticked in `board/done.md` | Find source issue, update issue-level schedule.json |
| Event edited in `board/p0.md` | Find source issue, update issue-level schedule.json |

After an issue-level schedule.json update, aggregation re-runs to keep board-level files consistent. The watcher tracks the source of each change to avoid infinite loops.

History.csv and done.md graphs are **not** updated in real-time — only at end of day.

---

## What Enters schedule.json

| Item | Enters schedule.json? | Section |
|---|---|---|
| Self-scheduled work session today | Yes | `p0` |
| Self-scheduled work session this week | Yes | `p1` |
| Completed event (last 3 days) | Yes | `done` |
| Future event (not this week) | No | `p2.md` only |
| External meetings, work calls, appointments | No | Separate calendar |
| Events older than 3 days | No | `history.csv` only |
| Shabits recurring habits | Yes (in shabits/schedule.json) | `p0` |

---

## CalDAV Generation

**Scope:** Only self-scheduled board work sessions enter CalDAV from the board. External meetings, work calls, or appointments are kept in a separate calendar and never put into schedule.json or the board.

Everything in schedule.json (`p0`, `p1`, `done`) syncs to CalDAV. `p2` has no CalDAV representation.

### VEVENT (calendar blocks)

- One per time_block per event
- Filename: `event-{issue}-{event-id}-{date}-{start}.ics`
- UID: UUID5(NAMESPACE_DNS, `event-{issue}-{event-id}-{date}-{start}`)
- `CATEGORIES:board-event,{issue}` — e.g. `CATEGORIES:board-event,cv`
- Stays in CalDAV permanently — calendar record of work sessions
- Generated for p0 and p1 events with time_blocks; `done` events update their existing VEVENT DESCRIPTION in place
- Tasks always appear in `DESCRIPTION` as a plain text list (one per line, no checkboxes):
  ```
  DESCRIPTION:Install ROCm drivers\nConfigure PyTorch
  ```
- Shabits VEVENTs are generated fresh per day (no RRULE) so each occurrence can carry its own DESCRIPTION; handled by `shabits-caldav` separately

### VTODO (tasks)

- One per task — **p0 and p1**
- Filename: `task-{issue}-{event-id}-{task-id}.ics`
- UID: UUID5(NAMESPACE_DNS, `task-{issue}-{event-id}-{task-id}`)
- `CATEGORIES:board-task,{issue}` — e.g. `CATEGORIES:board-task,cv`
- STATUS: NEEDS-ACTION / COMPLETED
- `DUE`: set to end of event time_block (p0), or event `due` date (p1 without time_blocks)
- When a task moves to `done`, its VTODO STATUS becomes COMPLETED — the VTODO remains in CalDAV for 3 days then is deleted

### CalDAV sync summary

| Section | VEVENT | VTODO |
|---|---|---|
| p0 (has time_blocks) | Yes | Yes, one per task |
| p1 (has time_blocks) | Yes | Yes, one per task |
| p1 (no time_blocks) | No | Yes, one per task with due date |
| done | Update DESCRIPTION only | Existing VTODOs stay as COMPLETED, deleted after 3 days |
| p2 | No | No |

### What replaces what

- Old `board-sync` (p0/p1/p2 directory scanning) → replaced by this CalDAV generator
- `shabits-caldav` → unchanged, habits remain a separate concern with fresh-per-day VEVENTs

---

## End-of-Day Sequence (systemd timer, 23:55)

Run per issue, then aggregate:

```
1. For each p0 event:
   a. All tasks done          → move to "done" section in schedule.json
   b. Unfinished + scheduled for tomorrow → keep in p0, update date
   c. Unfinished + not rescheduled       → move to p1

2. Prune "done" events older than 3 days: append to history.csv, remove from schedule.json

3. Append today's completed tasks + events to history.csv

4. Regenerate done.md from history.csv (last 3 days) + graphs
   - For shabits: flag yesterday's missed habits, mark "must complete today" if unconfirmed

5. Regenerate p0.md and p1.md for tomorrow
   - Night routine shabits appear in "Shabits — Last Night" section of tomorrow's p0.md

6. Run CalDAV generation → vdirsyncer sync (including VEVENT DESCRIPTION updates for "done" events)

7. Aggregate board-level files
```

## p2 → p1 Graduation

Always manual — you or Claude Code moves an event title from p2.md into p1.md and adds it to schedule.json with an optional due date. No automatic promotion.

---

## Aggregation

`board-aggregate` script merges all issues into board-level files:

- `board/p0.md` — all issues' p0, sorted chronologically across issues
- `board/p1.md` — all issues' p1, grouped by issue
- `board/p2.md` — all issues' p2, grouped by issue
- `board/done.md` — all issues' done, grouped by issue + graphs
- `board/schedule.json` — all issues' schedule.json merged
- `board/history.csv` — all issues' history.csv merged

Aggregation is triggered by:

- Any issue-level `schedule.json` change (file watcher)
- Any board-level md edit (file watcher, after propagating back to the source issue)
- End-of-day timer (always)

---

## Migration Plan

1. Move `board/cv/` → `board/issues/projects/cv/`
2. Move `board/mvg/`, `board/papers/`, `board/rl/` → `board/issues/reading-material/`
3. Move `board/work/` → `board/issues/work/`
4. Move `board/shabits/` → `board/issues/shabits/`
5. Delete `board/meditation/` — morning meditation is already a shabit
6. For each issue: convert `p0/`, `p1/`, `p2/` individual task `.md` files → entries in `p0.md`, `p1.md`, `p2.md`
7. Move `board/done/shabits.csv` → `board/issues/shabits/history.csv`
8. Move `board/shabits/charts/` → `board/issues/shabits/graphs/`
9. Create empty `history.csv` and `schedule.json` for each non-shabits issue
10. Remove old `board/p0/`, `board/p1/`, `board/p2/` empty directories

---

## Scripts Summary

| Script | Role |
|---|---|
| `board-generate` | schedule.json → p0.md / p1.md / done.md (per issue) |
| `board-sync` | schedule.json → ICS files + vdirsyncer (non-shabits events only) |
| `board-overflow` | end-of-day: p0→done/p1, prune, history.csv, done.md, CalDAV sync |
| `board-aggregate` | merge all issues → board-level files |
| `board-watch` | file watcher: md↔schedule.json bidirectional sync (issue and board level) + triggers aggregate |
| `board-pages` | generate done.md + graphs from history.csv (called by overflow) |

---

## SKILL.md

The current `board/SKILL.md` is for the old system and must be fully rewritten as part of this implementation. The new SKILL.md should document:

- The `issues/` directory layout and grouping folder rules
- How to read and write `schedule.json` (adding events, tasks, promoting p2→p1)
- How to interpret `p0.md`, `p1.md`, `p2.md`, `done.md`
- Which scripts to call for which operations
- The SMART task format and time-horizon lane definitions
- How CalDAV tags map to issues (`CATEGORIES:board-task,{issue}`)
- The `actual` field for recording real session times
