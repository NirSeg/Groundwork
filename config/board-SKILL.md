---
name: board
description: Manage the Groundwork board — schedule, tasks, priorities and CalDAV sync across all issues.
---

# Board

The board is a personal productivity system built around `schedule.json` as the source of truth. It aggregates all issues (projects, courses, habits) into a unified daily schedule.

## Structure

```
board/
├── p0.md          ← today's schedule (chronological, read to understand the day)
├── p1.md          ← this week's work
├── p2.md          ← future backlog (flat titles only)
├── done.md        ← last 3 days completions + graphs
├── schedule.json  ← aggregated source of truth (read-only at board level)
├── history.csv    ← all past tasks and events
└── issues/
    ├── shabits/               ← habits (no p1/p2)
    ├── projects/<name>/       ← symlink to ~/Projects/<name>/.board/
    ├── reading-material/<name>/  ← symlink to course/book repo .board/
    └── work/<name>/           ← symlink to work project .board/
```

Each issue owns its own `schedule.json`, `history.csv`, `p0.md`, `p1.md`, `p2.md`. The board-level files are aggregated views — never edit them directly.

## Mental Model

- **Goals** = Issues — active projects only. Added manually when you start working on something new.
- **Missions** = Events — a specific work session with a clear outcome (SMART applies to missions first).
- **Todos** = Tasks — SMART action items within a mission, sized to fit the time block.

## Priority Lanes — Time Horizon

| Lane | Horizon | Decision rule | In schedule.json |
|------|---------|---------------|-----------------|
| p0 | Today | Has a time block scheduled for today | `date` + `time_blocks` required |
| p1 | This week | Due or time-blocked within the current week | `due` and/or `time_blocks` optional |
| p2 | This month / coming months | Planned but not this week — may have due dates | Not present — p2.md only |

The question that determines lane is **when**. p2 is not a vague backlog — missions there are real planned work, just further out than this week.

## schedule.json Format (per issue)

```json
{
  "issue": "cv",
  "p0": [
    {
      "id": "event-id",
      "title": "Event title",
      "date": "2026-05-16",
      "time_blocks": [["10:00", "12:00"]],
      "tasks": [
        {"id": "t1", "text": "SMART task description", "done": false}
      ]
    }
  ],
  "p1": [
    {
      "id": "event-id",
      "title": "Event title",
      "due": "2026-05-20",
      "time_blocks": [],
      "tasks": []
    }
  ],
  "done": [
    {
      "id": "event-id",
      "title": "Completed event",
      "date": "2026-05-14",
      "time_blocks": [["14:00", "16:00"]],
      "tasks": [{"id": "t1", "text": "Task", "done": true}]
    }
  ]
}
```

`done` section holds last 3 days only — pruned automatically at end of day.

## Tasks — SMART Format

Every task must be:
- **Specific** — clear action, not vague
- **Measurable** — you know when it's done
- **Achievable** — fits within the time block
- **Relevant** — serves the event's goal
- **Time-bounded** — implied by the event's time block

Good: `"Implement forward pass for Gaussian rasterizer (single tile)"`
Bad: `"Work on rasterizer"`

## How to Add a Task to Today's Schedule

Edit the issue's `schedule.json` — find the event in `p0`, add to its `tasks` array:

```json
{"id": "t3", "text": "Your SMART task", "done": false}
```

The file watcher regenerates `p0.md` automatically. Or edit `p0.md` directly — the watcher syncs back to `schedule.json`.

## How to Add a New Event to Today (p0)

Add to the issue's `schedule.json` under `p0`:

```json
{
  "id": "short-kebab-id",
  "title": "What you're working on",
  "date": "2026-05-16",
  "time_blocks": [["14:00", "16:00"]],
  "tasks": []
}
```

## How to Schedule a p1 Event for Today

Move the event from `p1` to `p0` in the issue's `schedule.json` and add `date` + `time_blocks`.

## How to Promote p2 → p1

Add the event title to the issue's `schedule.json` under `p1` with an optional `due` date. Remove it from `p2.md`.

## How to Add a New Issue

1. Create `.board/` inside the project repo with the standard layout
2. Create a symlink: `ln -s ~/Work/MyProject/.board/ ~/Board/board/issues/work/my_project`
3. Run `board-aggregate` to include it in the board-level files

## Scripts

| Command | What it does |
|---------|-------------|
| `board-generate` | Regenerate p0.md / p1.md from schedule.json |
| `board-sync` | Generate CalDAV ICS files + run vdirsyncer |
| `board-aggregate` | Merge all issues into board-level files |
| `board-overflow` | End-of-day: move unfinished p0 → p1, update history |
| `board-pages` | Regenerate done.md + graphs from history.csv |

## CalDAV Tags

Events and tasks appear on your phone with issue tags:
- Calendar events: `CATEGORIES:board-event,{issue}`
- Tasks: `CATEGORIES:board-task,{issue}`

Filter by issue name in your phone's tasks app to see only one project at a time.

## End of Day (automatic at 23:55)

- Unfinished p0 events → moved to p1 (unless rescheduled for tomorrow)
- Completed events → moved to `done` section in schedule.json
- `done` events older than 3 days → pruned
- history.csv and done.md updated
- Board aggregated for tomorrow
