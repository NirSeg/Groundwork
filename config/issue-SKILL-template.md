---
name: <issue-name>
description: Board for <Project Name> — <one line about what this project is>.
---

# <Project Name>

<2-3 sentences about what this project is and what you're trying to achieve.>

## Current State

- **p0** — what's scheduled for today
- **p1** — what's due this week
- **p2** — future backlog

Read `p0.md` to see today's work. Read `p1.md` for this week's plan.

## Domain Context

<Key concepts, terminology, or background Claude needs to understand tasks in this project. Keep it short — only what affects how tasks should be written or prioritized.>

## How to Add Work Here

To add a task to today's schedule, edit `schedule.json` → find the event in `p0` → add to `tasks`:

```json
{"id": "t-new", "text": "SMART task description", "done": false}
```

To add a new event this week, add to `p1` in `schedule.json`:

```json
{
  "id": "short-kebab-id",
  "title": "What needs to get done",
  "due": "2026-05-20",
  "tasks": []
}
```

To dump a future idea, append a line to `p2.md`:

```markdown
## Future idea title
```

## Constraints

<Any project-specific rules — e.g. "always write tests before implementation", "don't touch the prod DB directly", "tasks must map to a GitHub issue".>
