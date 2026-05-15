# Board Redesign Spec

## Goal

Restructure the Groundwork board from a flat topic-folder layout into a hierarchical `issues/` system driven by `schedule.json` as the source of truth, with Eisenhower-mapped priorities, bidirectional md↔json sync, CalDAV generation, and end-of-day overflow logic.

---

## Directory Structure

```
board/
├── p0.md              ← generated, today's schedule (chronological, aggregated)
├── p1.md              ← generated, this week (aggregated)
├── p2.md              ← flat list, manually maintained (aggregated)
├── done.md            ← last 3 days completions + graphs (generated, updated EOD)
├── schedule.json      ← merged from all issues (generated)
├── history.csv        ← all past tasks + events (merged, updated EOD)
├── SKILL.md
├── graphs/
└── issues/
    ├── shabits/           ← no p1/p2
    │   ├── p0.md
    │   ├── done.md
    │   ├── history.csv
    │   ├── schedule.json
    │   ├── SKILL.md
    │   └── graphs/
    ├── projects/          ← grouping folder only, no own files
    │   └── cv/
    │       ├── p0.md
    │       ├── p1.md
    │       ├── p2.md
    │       ├── done.md
    │       ├── history.csv
    │       ├── schedule.json
    │       ├── SKILL.md
    │       └── graphs/
    ├── reading-material/  ← grouping folder only
    │   ├── mvg/
    │   ├── papers/
    │   └── rl/
    └── work/              ← grouping folder only
        └── ai_therapist/
```

Grouping folders (`projects/`, `reading-material/`, `work/`) are pure containers with no files of their own.

---

## Eisenhower Mapping

| Lane | Quadrant | Meaning |
|------|----------|---------|
| p0 | Urgent + Important | Scheduled for today — has time blocks |
| p1 | Important, not urgent | Due this week — may have time blocks and/or due date |
| p2 | Backlog | Future ideas — flat list of event titles, no dates |

Tasks follow the SMART model (Specific, Measurable, Achievable, Relevant, Time-bounded).

---

## schedule.json Format (per issue)

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
        {"id": "t1", "text": "Reproduce crash", "done": true}
      ]
    }
  ]
}
```

- `p0` events: require `date` + `time_blocks`
- `p1` events: optional `due` and/or `time_blocks`
- `p2`: not in schedule.json — lives only in p2.md
- `done`: last 3 days of completed events only, pruned at EOD
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

Two ICS types generated from schedule.json `p0` and `p1` sections:

### VEVENT (calendar blocks)
- One per time_block per event
- Filename: `event-{issue}-{event-id}-{date}-{start}.ics`
- UID: UUID5(NAMESPACE_DNS, `event-{issue}-{event-id}-{date}-{start}`)
- `CATEGORIES:board-event,{issue}` — e.g. `CATEGORIES:board-event,cv`
- Stays in CalDAV permanently — calendar record of work sessions
- Generated for both p0 (today) and p1 events that have time_blocks

### VTODO (tasks)
- One per task
- Filename: `task-{issue}-{event-id}-{task-id}-{date}.ics`
- UID: UUID5(NAMESPACE_DNS, `task-{issue}-{event-id}-{task-id}-{date}`)
- `CATEGORIES:board-task,{issue}` — e.g. `CATEGORIES:board-task,cv`
- STATUS: NEEDS-ACTION / COMPLETED
- Deleted 3 days after completion
- Generated for p0 tasks; p1 events without time_blocks get a single VTODO with due date

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

2. Prune "done" events older than 3 days from schedule.json

3. Append today's completed tasks + events to history.csv

4. Regenerate done.md from history.csv (last 3 days) + graphs

5. Regenerate p0.md and p1.md for tomorrow

6. Run CalDAV generation → vdirsyncer sync

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
| `board-overflow` | end-of-day: p0→done/p1, prune, history.csv, done.md |
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
- The SMART task format and Eisenhower lane definitions
- How CalDAV tags map to issues (`CATEGORIES:board-task,{issue}`)
