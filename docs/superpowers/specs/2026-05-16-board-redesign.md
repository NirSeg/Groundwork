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
├── done.md            ← daily review: last 3 days completions + graphs + missed shabits (generated, updated EOD)
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
- Recurring events (shabits): include `"recurring": {"days": ["Mon", ...]}` field, no RRULE in CalDAV

Board-level `schedule.json` is merged from all issues at aggregation time.

---

## p0.md Format

Events sorted chronologically by first time_block start. Events without time blocks go under `## Unscheduled` at the bottom.

```markdown
# CV — Fri 2026-05-16

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

Daily review interface generated from `history.csv` and `shabits.csv`. Updated at end of day only.

Content per issue (last 3 days):
- Completed events with their tasks, grouped by date
- Completion graphs from `graphs/`

For shabits specifically:
- Shows which habits were missed yesterday
- Missed habits that were actually done but not ticked off can be retroactively marked complete
- Any habit missed yesterday that cannot be confirmed done is flagged **"must complete today"**

Night routine shabits (prepare-for-bed, evening meditation, read-before-sleep) are treated as the next morning's tasks — they appear in the next day's `done.md` review window.

---

## Bidirectional Sync

File watcher monitors all issue-level `p0.md`, `p1.md`, and `schedule.json` files.

### md → schedule.json (real-time)

| Change in md | Engine action |
|---|---|
| `[x]` task checked | `done: true` in schedule.json |
| New `- [ ] text` line added | New task entry in event |
| New `## Title  HH:MM–HH:MM` heading | New p0 event in schedule.json |
| New `## Title  (due: ...)` heading | New p1 event in schedule.json |
| Event title renamed | Update title in schedule.json |

### schedule.json → md (real-time)

| Change in schedule.json | Engine action |
|---|---|
| Event added/edited | Regenerate relevant md file |
| Task marked done | Check off `[x]` in md |
| Event removed | Remove from md |

History.csv and done.md are **not** updated in real-time — only at end of day.

---

## CalDAV Generation

Two ICS types generated from schedule.json `p0`, `p1`, and `done` sections:

### VEVENT (calendar blocks)

- One per time_block per event
- Filename: `event-{issue}-{event-id}-{date}-{start}.ics`
- UID: UUID5(NAMESPACE_DNS, `event-{issue}-{event-id}-{date}-{start}`)
- `CATEGORIES:board-event,{issue}` — e.g. `CATEGORIES:board-event,cv`
- Stays in CalDAV permanently — calendar record of work sessions
- Generated for p0 and p1 events that have time_blocks; `done` events update their existing VEVENT in place
- Tasks are always included in the `DESCRIPTION` field (one per line, `[x]` or `[ ]` prefix)
- Any edit to tasks in `done` section of schedule.json triggers a VEVENT DESCRIPTION update on next CalDAV sync

### VTODO (tasks)

- One per task — **p0 only**
- Filename: `task-{issue}-{event-id}-{task-id}-{date}.ics`
- UID: UUID5(NAMESPACE_DNS, `task-{issue}-{event-id}-{task-id}-{date}`)
- `CATEGORIES:board-task,{issue}` — e.g. `CATEGORIES:board-task,cv`
- STATUS: NEEDS-ACTION / COMPLETED
- Deleted 3 days after completion
- p1 events are **not** represented as VTODOs — tasks for p1 events appear only in the DESCRIPTION field of the corresponding VEVENT

### What replaces what

- Old `board-sync` (p0/p1/p2 directory scanning) → replaced by this CalDAV generator
- `shabits-caldav` → unchanged, habits remain a separate concern

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

Aggregation triggers:

- Any issue-level `schedule.json` change (file watcher)
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
| `board-generate` | schedule.json → p0.md / p1.md (per issue) |
| `board-sync` | schedule.json → ICS files + vdirsyncer (replaces old board-sync) |
| `board-overflow` | end-of-day: p0→history.csv/p1, done.md, CalDAV sync |
| `board-aggregate` | merge all issues → board-level files |
| `board-watch` | file watcher: md↔schedule.json bidirectional sync + triggers aggregate |
| `board-pages` | generate done.md + graphs from history.csv (called by overflow) |

---

## SKILL.md

The current `board/SKILL.md` is for the old system and must be fully rewritten as part of this implementation. The new SKILL.md should document:

- The `issues/` directory layout and grouping folder rules
- How to read and write `schedule.json` (adding events, tasks, promoting p2→p1)
- How to interpret `p0.md`, `p1.md`, `p2.md`
- Which scripts to call for which operations
- The SMART task format and time-horizon lane definitions
- How CalDAV tags map to issues (`CATEGORIES:board-task,{issue}`)
