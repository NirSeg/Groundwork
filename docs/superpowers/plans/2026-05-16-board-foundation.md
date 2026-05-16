# Board Redesign — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate the existing flat board to the new `issues/` hierarchy and build `board-generate` + `board-aggregate` so every issue has a working `schedule.json` driving its `p0.md`, `p1.md`, `done.md`, and the board-level files are a merged view across all issues.

**Architecture:** A shared `board_schema.py` module owns schedule.json validation and I/O. `board-generate` reads one issue's `schedule.json` and writes its three md files. `board-aggregate` traverses `board/issues/` (following symlinks), merges all schedules and histories, and writes board-level files. `board-migrate` is a one-time script that converts the old flat layout to the new hierarchy. All scripts are in `scripts/`, tests in `tests/`.

**Tech Stack:** Python 3, pathlib, json, pytest. No new dependencies.

---

## File Map

| Action | Path | Responsibility |
|---|---|---|
| Create | `scripts/board_schema.py` | schedule.json validation, load, save |
| Create | `scripts/board-generate` | schedule.json → p0.md / p1.md / done.md (per issue) |
| Create | `scripts/board-aggregate` | merge all issues → board-level files |
| Create | `scripts/board-migrate` | one-time migration from old flat board |
| Create | `tests/test_board_schema.py` | schema validation tests |
| Create | `tests/test_board_generate.py` | md generation tests |
| Create | `tests/test_board_aggregate.py` | aggregation tests |
| Create | `tests/test_board_migrate.py` | migration tests |
| Modify | `install.sh` | install new scripts + scaffold directory structure |

---

## Task 1: board_schema.py — schedule.json validation and I/O

**Files:**
- Create: `scripts/board_schema.py`
- Test: `tests/test_board_schema.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_board_schema.py
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
from board_schema import load_schedule, save_schedule, validate_schedule


def _valid():
    return {
        "issue": "cv",
        "p0": [
            {
                "id": "e1",
                "title": "Event",
                "date": "2026-05-16",
                "time_blocks": [["10:00", "12:00"]],
                "tasks": [{"id": "t1", "text": "Do thing", "done": False}],
            }
        ],
        "p1": [],
        "done": [],
    }


def test_validate_valid_schedule():
    assert validate_schedule(_valid())["issue"] == "cv"


def test_validate_missing_issue_field():
    data = _valid()
    del data["issue"]
    with pytest.raises(ValueError, match="missing 'issue'"):
        validate_schedule(data)


def test_validate_p0_event_missing_id():
    data = _valid()
    del data["p0"][0]["id"]
    with pytest.raises(ValueError, match="missing 'id'"):
        validate_schedule(data)


def test_validate_p0_event_missing_date():
    data = _valid()
    del data["p0"][0]["date"]
    with pytest.raises(ValueError, match="p0 event missing 'date'"):
        validate_schedule(data)


def test_validate_p0_event_empty_time_blocks():
    data = _valid()
    data["p0"][0]["time_blocks"] = []
    with pytest.raises(ValueError, match="p0 event missing 'time_blocks'"):
        validate_schedule(data)


def test_validate_task_missing_done_field():
    data = _valid()
    del data["p0"][0]["tasks"][0]["done"]
    with pytest.raises(ValueError, match="task missing required fields"):
        validate_schedule(data)


def test_load_and_save_roundtrip():
    data = {"issue": "cv", "p0": [], "p1": [], "done": []}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "schedule.json"
        save_schedule(path, data)
        loaded = load_schedule(path)
        assert loaded == data


def test_save_writes_valid_json():
    data = {"issue": "cv", "p0": [], "p1": [], "done": []}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "schedule.json"
        save_schedule(path, data)
        raw = json.loads(path.read_text())
        assert raw["issue"] == "cv"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_board_schema.py -v
```

Expected: `ModuleNotFoundError: No module named 'board_schema'`

- [ ] **Step 3: Implement board_schema.py**

```python
# scripts/board_schema.py
"""schedule.json validation and I/O."""
import json
from pathlib import Path


def _validate_event(event, section):
    for field in ("id", "title"):
        if field not in event:
            raise ValueError(f"{section} event missing '{field}': {event}")
    if section == "p0":
        if "date" not in event:
            raise ValueError(f"p0 event missing 'date': {event}")
        if not event.get("time_blocks"):
            raise ValueError(f"p0 event missing 'time_blocks': {event}")
    for task in event.get("tasks", []):
        if not all(k in task for k in ("id", "text", "done")):
            raise ValueError(f"task missing required fields: {task}")


def validate_schedule(data):
    if "issue" not in data:
        raise ValueError("schedule.json missing 'issue' field")
    for section in ("p0", "p1", "done"):
        for event in data.get(section, []):
            _validate_event(event, section)
    return data


def load_schedule(path):
    data = json.loads(Path(path).read_text())
    return validate_schedule(data)


def save_schedule(path, data):
    validate_schedule(data)
    Path(path).write_text(json.dumps(data, indent=2) + "\n")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_board_schema.py -v
```

Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add scripts/board_schema.py tests/test_board_schema.py
git commit -m "feat: add board_schema.py — schedule.json validation and I/O"
```

---

## Task 2: board-generate — schedule.json → md files

**Files:**
- Create: `scripts/board-generate`
- Test: `tests/test_board_generate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_board_generate.py
import importlib.util
import sys
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load():
    sys.path.insert(0, "scripts")
    loader = SourceFileLoader("board_generate", "scripts/board-generate")
    spec = importlib.util.spec_from_loader("board_generate", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


bg = _load()


def _sched(p0=None, p1=None, done=None):
    return {"issue": "cv", "p0": p0 or [], "p1": p1 or [], "done": done or []}


def _event(id_, title, date_str, start="10:00", end="12:00", tasks=None):
    return {
        "id": id_,
        "title": title,
        "date": date_str,
        "time_blocks": [[start, end]],
        "tasks": tasks or [],
    }


def _task(id_, text, done=False):
    return {"id": id_, "text": text, "done": done}


# --- p0 ---

def test_p0_shows_event_heading_with_time():
    s = _sched(p0=[_event("e1", "Set up ROCm", "2026-05-16")])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert "## Set up ROCm  10:00–12:00" in out


def test_p0_shows_unchecked_task():
    s = _sched(p0=[_event("e1", "Session", "2026-05-16",
                           tasks=[_task("t1", "Install drivers")])])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert "- [ ] Install drivers" in out


def test_p0_shows_checked_task():
    s = _sched(p0=[_event("e1", "Session", "2026-05-16",
                           tasks=[_task("t1", "Install drivers", done=True)])])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert "- [x] Install drivers" in out


def test_p0_orders_events_chronologically():
    s = _sched(p0=[
        _event("e2", "Afternoon", "2026-05-16", "14:00", "16:00"),
        _event("e1", "Morning", "2026-05-16", "09:00", "11:00"),
    ])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert out.index("Morning") < out.index("Afternoon")


def test_p0_excludes_events_for_other_dates():
    s = _sched(p0=[_event("e1", "Yesterday event", "2026-05-15")])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert "Yesterday event" not in out


def test_p0_night_routine_appears_in_last_night_section():
    s = _sched(p0=[{
        "id": "prepare-for-bed",
        "title": "Prepare for bed",
        "date": "2026-05-15",
        "time_blocks": [["21:30", "21:45"]],
        "tasks": [_task("t1", "Prepare for bed")],
    }])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert "Shabits — Last Night" in out
    assert "Prepare for bed" in out


def test_p0_night_routine_not_shown_when_date_is_today():
    s = _sched(p0=[{
        "id": "prepare-for-bed",
        "title": "Prepare for bed",
        "date": "2026-05-16",
        "time_blocks": [["21:30", "21:45"]],
        "tasks": [],
    }])
    out = bg.generate_p0(s, date(2026, 5, 16))
    assert "Shabits — Last Night" not in out


# --- p1 ---

def test_p1_shows_event_title():
    s = _sched(p1=[{"id": "e1", "title": "Implement Gaussians",
                    "due": "2026-05-20", "time_blocks": [], "tasks": []}])
    out = bg.generate_p1(s)
    assert "Implement Gaussians" in out


def test_p1_shows_due_and_time_blocks():
    s = _sched(p1=[{"id": "e1", "title": "Task",
                    "due": "2026-05-20",
                    "time_blocks": [["10:00", "12:00"]],
                    "tasks": []}])
    out = bg.generate_p1(s)
    assert "due: 2026-05-20" in out
    assert "10:00–12:00" in out


# --- done ---

def test_done_shows_completed_event():
    s = _sched(done=[{
        "id": "e1", "title": "Debug loader", "date": "2026-05-14",
        "time_blocks": [["14:00", "16:00"]],
        "tasks": [_task("t1", "Reproduce crash", done=True)],
    }])
    out = bg.generate_done(s)
    assert "Debug loader" in out
    assert "- [x] Reproduce crash" in out


def test_done_shows_actual_time_when_present():
    s = _sched(done=[{
        "id": "e1", "title": "Session", "date": "2026-05-14",
        "time_blocks": [["10:00", "12:00"]], "actual": ["10:05", "11:50"],
        "tasks": [],
    }])
    out = bg.generate_done(s)
    assert "actual: 10:05–11:50" in out
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_board_generate.py -v
```

Expected: collection error — `scripts/board-generate` not found

- [ ] **Step 3: Implement board-generate**

```python
#!/usr/bin/env python3
"""
board-generate — generate p0.md, p1.md, done.md from an issue's schedule.json

Usage:
  board-generate <issue-path>          regenerate all three md files
  board-generate <issue-path> p0       regenerate p0.md only
  board-generate <issue-path> p1       regenerate p1.md only
  board-generate <issue-path> done     regenerate done.md only
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from board_schema import load_schedule

NIGHT_ROUTINE_IDS = {"prepare-for-bed", "evening-meditation", "read-before-sleep"}


def _fmt_blocks(time_blocks):
    if not time_blocks:
        return ""
    return "  " + "  ".join(f"{s}–{e}" for s, e in time_blocks)


def generate_p0(schedule, today=None):
    today = today or date.today()
    issue = schedule["issue"].upper()
    date_str = today.strftime("%a %Y-%m-%d")
    lines = [f"# {issue} — {date_str}", ""]

    # Night routine from yesterday: p0 events with night-routine IDs dated before today
    night = [
        e for e in schedule.get("p0", [])
        if e.get("id") in NIGHT_ROUTINE_IDS and e.get("date") != str(today)
    ]
    if night:
        lines.append("## Shabits — Last Night")
        for event in night:
            for task in event.get("tasks", []):
                mark = "x" if task["done"] else " "
                lines.append(f"- [{mark}] {task['text']}")
        lines.append("")

    today_events = [e for e in schedule.get("p0", []) if e.get("date") == str(today)]
    scheduled = sorted(
        [e for e in today_events if e.get("time_blocks")],
        key=lambda e: e["time_blocks"][0][0],
    )
    unscheduled = [e for e in today_events if not e.get("time_blocks")]

    for event in scheduled:
        lines.append(f"## {event['title']}{_fmt_blocks(event['time_blocks'])}")
        for task in event.get("tasks", []):
            mark = "x" if task["done"] else " "
            lines.append(f"- [{mark}] {task['text']}")
        lines.append("")

    if unscheduled:
        lines.append("## Unscheduled")
        for event in unscheduled:
            lines.append(f"### {event['title']}")
            for task in event.get("tasks", []):
                mark = "x" if task["done"] else " "
                lines.append(f"- [{mark}] {task['text']}")
            lines.append("")

    return "\n".join(lines)


def generate_p1(schedule):
    issue = schedule["issue"].upper()
    today = date.today()
    lines = [f"# {issue} — Week of {today}", ""]

    for event in schedule.get("p1", []):
        meta = []
        if event.get("due"):
            meta.append(f"due: {event['due']}")
        for s, e in event.get("time_blocks", []):
            meta.append(f"{s}–{e}")
        suffix = f"  ({', '.join(meta)})" if meta else ""
        lines.append(f"## {event['title']}{suffix}")
        for task in event.get("tasks", []):
            mark = "x" if task["done"] else " "
            lines.append(f"- [{mark}] {task['text']}")
        lines.append("")

    return "\n".join(lines)


def generate_done(schedule):
    issue = schedule["issue"].upper()
    lines = [f"# {issue} — Recent", ""]

    for event in schedule.get("done", []):
        actual = event.get("actual")
        actual_str = f"  (actual: {actual[0]}–{actual[1]})" if actual else ""
        time_str = _fmt_blocks(event.get("time_blocks", []))
        date_str = f"  [{event.get('date', '')}]" if event.get("date") else ""
        lines.append(f"## {event['title']}{time_str}{actual_str}{date_str}")
        for task in event.get("tasks", []):
            mark = "x" if task["done"] else " "
            lines.append(f"- [{mark}] {task['text']}")
        lines.append("")

    return "\n".join(lines)


def generate_all(issue_path, today=None):
    issue_path = Path(issue_path)
    schedule = load_schedule(issue_path / "schedule.json")
    today = today or date.today()
    (issue_path / "p0.md").write_text(generate_p0(schedule, today))
    (issue_path / "p1.md").write_text(generate_p1(schedule))
    (issue_path / "done.md").write_text(generate_done(schedule))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    issue_path = Path(args[0])
    target = args[1] if len(args) > 1 else "all"
    schedule = load_schedule(issue_path / "schedule.json")
    today = date.today()
    if target in ("p0", "all"):
        (issue_path / "p0.md").write_text(generate_p0(schedule, today))
    if target in ("p1", "all"):
        (issue_path / "p1.md").write_text(generate_p1(schedule))
    if target in ("done", "all"):
        (issue_path / "done.md").write_text(generate_done(schedule))
    print(f"  Generated {target} for {schedule['issue']}")
```

- [ ] **Step 4: Make executable**

```bash
chmod +x scripts/board-generate
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_board_generate.py -v
```

Expected: 13 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/board-generate tests/test_board_generate.py
git commit -m "feat: add board-generate — schedule.json to p0/p1/done.md"
```

---

## Task 3: board-aggregate — merge all issues into board-level files

**Files:**
- Create: `scripts/board-aggregate`
- Test: `tests/test_board_aggregate.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_board_aggregate.py
import importlib.util
import json
import sys
import tempfile
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load():
    sys.path.insert(0, "scripts")
    loader = SourceFileLoader("board_aggregate", "scripts/board-aggregate")
    spec = importlib.util.spec_from_loader("board_aggregate", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


ba = _load()


def _make_issue(root, group, name, schedule, p2="", history=""):
    path = root / "issues" / group / name if group else root / "issues" / name
    path.mkdir(parents=True, exist_ok=True)
    (path / "schedule.json").write_text(json.dumps(schedule))
    (path / "p2.md").write_text(p2 or f"# {name.upper()}\n")
    hist = history or "date,event_id,event_title,task_id,task_text\n"
    (path / "history.csv").write_text(hist)
    return path


def _empty_sched(name):
    return {"issue": name, "p0": [], "p1": [], "done": []}


def test_find_issues_finds_project_issue():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_issue(root, "projects", "cv", _empty_sched("cv"))
        issues = ba.find_issues(root / "issues")
        assert any(name == "cv" for name, _, _ in issues)


def test_find_issues_finds_direct_issue():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_issue(root, None, "shabits", _empty_sched("shabits"))
        issues = ba.find_issues(root / "issues")
        assert any(name == "shabits" for name, _, _ in issues)


def test_aggregate_p0_groups_by_issue():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sched = {
            "issue": "cv",
            "p0": [{
                "id": "e1", "title": "Set up ROCm",
                "date": "2026-05-16",
                "time_blocks": [["10:00", "12:00"]],
                "tasks": [],
            }],
            "p1": [], "done": [],
        }
        _make_issue(root, "projects", "cv", sched)
        issues = ba.find_issues(root / "issues")
        out = ba.aggregate_p0(issues, date(2026, 5, 16))
        assert "## CV" in out
        assert "Set up ROCm" in out


def test_aggregate_p0_excludes_events_for_other_dates():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        sched = {
            "issue": "cv",
            "p0": [{"id": "e1", "title": "Old event", "date": "2026-05-15",
                    "time_blocks": [["10:00", "12:00"]], "tasks": []}],
            "p1": [], "done": [],
        }
        _make_issue(root, "projects", "cv", sched)
        issues = ba.find_issues(root / "issues")
        out = ba.aggregate_p0(issues, date(2026, 5, 16))
        assert "Old event" not in out


def test_aggregate_p1_lists_all_issues():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_issue(root, "projects", "cv", {
            "issue": "cv",
            "p0": [],
            "p1": [{"id": "e1", "title": "Implement Gaussians",
                    "due": "2026-05-20", "time_blocks": [], "tasks": []}],
            "done": [],
        })
        _make_issue(root, "reading-material", "mvg", {
            "issue": "mvg",
            "p0": [],
            "p1": [{"id": "e2", "title": "Read ch1",
                    "due": "2026-05-18", "time_blocks": [], "tasks": []}],
            "done": [],
        })
        issues = ba.find_issues(root / "issues")
        out = ba.aggregate_p1(issues)
        assert "## CV" in out
        assert "Implement Gaussians" in out
        assert "## MVG" in out
        assert "Read ch1" in out


def test_aggregate_history_merges_rows_with_single_header():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        header = "date,event_id,event_title,task_id,task_text"
        _make_issue(root, "projects", "cv", _empty_sched("cv"),
                    history=header + "\n2026-05-14,e1,Debug,t1,Reproduce crash\n")
        _make_issue(root, None, "shabits", _empty_sched("shabits"),
                    history=header + "\n2026-05-14,e2,Morning,t1,Routine\n")
        issues = ba.find_issues(root / "issues")
        out = ba.aggregate_history(issues)
        assert "e1,Debug" in out
        assert "e2,Morning" in out
        assert out.count(header) == 1


def test_aggregate_schedule_merges_all_issues():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _make_issue(root, "projects", "cv", _empty_sched("cv"))
        _make_issue(root, None, "shabits", _empty_sched("shabits"))
        issues = ba.find_issues(root / "issues")
        schedules = ba.aggregate_schedule(issues)
        issue_names = [s["issue"] for s in schedules]
        assert "cv" in issue_names
        assert "shabits" in issue_names


def test_aggregate_skips_issue_with_no_schedule_json():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Create an issue dir with no schedule.json
        (root / "issues" / "projects" / "empty").mkdir(parents=True)
        (root / "issues" / "projects" / "empty" / "p2.md").write_text("# EMPTY\n")
        issues = ba.find_issues(root / "issues")
        # Should not raise
        out = ba.aggregate_p0(issues, date(2026, 5, 16))
        assert isinstance(out, str)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_board_aggregate.py -v
```

Expected: collection error — `scripts/board-aggregate` not found

- [ ] **Step 3: Implement board-aggregate**

```python
#!/usr/bin/env python3
"""
board-aggregate — merge all issues into board-level files

Usage:
  board-aggregate      regenerate all board-level files
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from board_schema import load_schedule

BOARD_ROOT = Path.home() / "Board" / "board"
GROUPING_DIRS = {"projects", "reading-material", "work"}


def find_issues(issues_root):
    """Return list of (name, group, resolved_path) for all issues. Follows symlinks."""
    issues = []
    issues_root = Path(issues_root)
    if not issues_root.exists():
        return issues
    for entry in sorted(issues_root.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name in GROUPING_DIRS:
            for child in sorted(entry.iterdir()):
                if child.is_dir():
                    issues.append((child.name, entry.name, child.resolve()))
        else:
            issues.append((entry.name, None, entry.resolve()))
    return issues


def aggregate_p0(issues, today=None):
    today = today or date.today()
    lines = [f"# Board — {today.strftime('%a %Y-%m-%d')}", ""]

    # Collect all today's events with time_blocks, keyed by issue label
    by_issue = {}
    for name, group, path in issues:
        sched_path = path / "schedule.json"
        if not sched_path.exists():
            continue
        schedule = load_schedule(sched_path)
        label = name.upper().replace("_", " ")
        events = [
            e for e in schedule.get("p0", [])
            if e.get("date") == str(today) and e.get("time_blocks")
        ]
        if events:
            by_issue[label] = sorted(events, key=lambda e: e["time_blocks"][0][0])

    # Sort issues by earliest event start
    sorted_issues = sorted(
        by_issue.items(),
        key=lambda kv: kv[1][0]["time_blocks"][0][0],
    )

    for label, events in sorted_issues:
        lines.append(f"## {label}")
        for event in events:
            tb = "  " + "  ".join(f"{s}–{e}" for s, e in event["time_blocks"])
            lines.append(f"### {event['title']}{tb}")
            for task in event.get("tasks", []):
                mark = "x" if task["done"] else " "
                lines.append(f"- [{mark}] {task['text']}")
            lines.append("")

    return "\n".join(lines)


def aggregate_p1(issues):
    today = date.today()
    lines = [f"# Board — Week of {today}", ""]
    for name, group, path in issues:
        sched_path = path / "schedule.json"
        if not sched_path.exists():
            continue
        schedule = load_schedule(sched_path)
        p1 = schedule.get("p1", [])
        if not p1:
            continue
        label = name.upper().replace("_", " ")
        lines.append(f"## {label}")
        for event in p1:
            meta = []
            if event.get("due"):
                meta.append(f"due: {event['due']}")
            for s, e in event.get("time_blocks", []):
                meta.append(f"{s}–{e}")
            suffix = f"  ({', '.join(meta)})" if meta else ""
            lines.append(f"### {event['title']}{suffix}")
        lines.append("")
    return "\n".join(lines)


def aggregate_p2(issues):
    lines = ["# Board — Future", ""]
    for name, group, path in issues:
        p2_path = path / "p2.md"
        if not p2_path.exists():
            continue
        content = p2_path.read_text().strip()
        non_header = [l for l in content.splitlines() if not l.startswith("# ")]
        if not any(l.strip() for l in non_header):
            continue
        label = name.upper().replace("_", " ")
        lines.append(f"## {label}")
        lines.extend(non_header)
        lines.append("")
    return "\n".join(lines)


def aggregate_schedule(issues):
    result = []
    for name, group, path in issues:
        sched_path = path / "schedule.json"
        if sched_path.exists():
            result.append(load_schedule(sched_path))
    return result


def aggregate_history(issues):
    header = "date,event_id,event_title,task_id,task_text"
    rows = []
    for name, group, path in issues:
        hist_path = path / "history.csv"
        if not hist_path.exists():
            continue
        lines = hist_path.read_text().splitlines()
        if len(lines) < 2:
            continue
        rows.extend(lines[1:])  # skip per-issue header
    return header + "\n" + "\n".join(rows) + "\n"


def run(board_root=None):
    br = Path(board_root) if board_root else BOARD_ROOT
    issues = find_issues(br / "issues")

    (br / "p0.md").write_text(aggregate_p0(issues))
    (br / "p1.md").write_text(aggregate_p1(issues))
    (br / "p2.md").write_text(aggregate_p2(issues))
    (br / "schedule.json").write_text(
        json.dumps(aggregate_schedule(issues), indent=2) + "\n"
    )
    (br / "history.csv").write_text(aggregate_history(issues))
    print(f"  Aggregated {len(issues)} issues → {br}")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Make executable**

```bash
chmod +x scripts/board-aggregate
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_board_aggregate.py -v
```

Expected: 9 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/board-aggregate tests/test_board_aggregate.py
git commit -m "feat: add board-aggregate — merge all issues into board-level files"
```

---

## Task 4: board-migrate — one-time migration from old flat board

**Files:**
- Create: `scripts/board-migrate`
- Test: `tests/test_board_migrate.py`

The migration converts the current `~/Board/board/` layout (flat issue folders with `p0/`, `p1/`, `p2/` subdirs of individual `.md` task files) into the new `issues/` hierarchy (each issue gets `schedule.json`, `p0.md`, `p1.md`, `p2.md`, `done.md`, `history.csv`, `graphs/`).

Old `p1/` task files (frontmatter + checkbox body) become `p1` events in `schedule.json` with their checkboxes parsed as tasks. Old `p2/` task files become flat `## Title` entries in `p2.md`. `shabits` is a special case: its `charts/` moves to `graphs/` and `done/shabits.csv` moves to `history.csv`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_board_migrate.py
import importlib.util
import json
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path


def _load():
    sys.path.insert(0, "scripts")
    loader = SourceFileLoader("board_migrate", "scripts/board-migrate")
    spec = importlib.util.spec_from_loader("board_migrate", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


bm = _load()


def _old_issue(root, name):
    """Create old-style issue directory with p0/, p1/, p2/ subdirs."""
    base = root / name
    for sub in ("p0", "p1", "p2", "done"):
        (base / sub).mkdir(parents=True)
    # p1 task
    (base / "p1" / "010_set-up-env.md").write_text(
        "---\nid: set-up-env\nsummary: Set up environment\n---\n\n"
        "- [ ] Install deps\n- [ ] Configure tools\n"
    )
    # p2 task
    (base / "p2" / "010_future-thing.md").write_text(
        "---\nid: future-thing\nsummary: Future thing\n---\n\n# Future thing\n"
    )
    return base


def test_parse_old_task_extracts_frontmatter():
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "task.md"
        f.write_text("---\nid: t1\nsummary: My task\n---\n\n# My task\n")
        meta, body = bm.parse_old_task(f)
        assert meta["id"] == "t1"
        assert meta["summary"] == "My task"


def test_tasks_from_body_extracts_unchecked():
    body = "- [ ] Do the thing\n- [ ] Another thing"
    tasks = bm.tasks_from_body(body)
    assert len(tasks) == 2
    assert tasks[0]["text"] == "Do the thing"
    assert tasks[0]["done"] is False


def test_tasks_from_body_extracts_checked():
    body = "- [x] Done already"
    tasks = bm.tasks_from_body(body)
    assert tasks[0]["done"] is True


def test_tasks_from_body_ignores_non_checkbox_lines():
    body = "Some description\n- [ ] Real task\nMore text"
    tasks = bm.tasks_from_body(body)
    assert len(tasks) == 1


def test_migrate_issue_creates_schedule_json_with_p1_events():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old = _old_issue(root / "old", "cv")
        new = root / "new" / "cv"
        bm.migrate_issue(old, new, "cv")
        schedule = json.loads((new / "schedule.json").read_text())
        assert schedule["issue"] == "cv"
        assert len(schedule["p1"]) == 1
        assert schedule["p1"][0]["id"] == "set-up-env"
        assert schedule["p1"][0]["title"] == "Set up environment"


def test_migrate_issue_converts_tasks_from_p1_body():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old = _old_issue(root / "old", "cv")
        new = root / "new" / "cv"
        bm.migrate_issue(old, new, "cv")
        schedule = json.loads((new / "schedule.json").read_text())
        tasks = schedule["p1"][0]["tasks"]
        assert len(tasks) == 2
        assert tasks[0]["text"] == "Install deps"
        assert tasks[1]["text"] == "Configure tools"


def test_migrate_issue_creates_p2_md_with_titles():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old = _old_issue(root / "old", "cv")
        new = root / "new" / "cv"
        bm.migrate_issue(old, new, "cv")
        p2 = (new / "p2.md").read_text()
        assert "## Future thing" in p2


def test_migrate_issue_creates_all_required_files():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old = _old_issue(root / "old", "cv")
        new = root / "new" / "cv"
        bm.migrate_issue(old, new, "cv")
        for fname in ("p0.md", "p1.md", "done.md", "history.csv", "schedule.json"):
            assert (new / fname).exists(), f"Missing {fname}"
        assert (new / "graphs").is_dir()


def test_migrate_shabits_moves_csv_to_history():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old_shabits = root / "shabits"
        old_shabits.mkdir()
        (old_shabits / "shabits.json").write_text("[]")
        (old_shabits / "charts").mkdir()
        (root / "done").mkdir()
        (root / "done" / "shabits.csv").write_text(
            "date,habit_id\n2026-05-14,morning-routine\n"
        )
        new_shabits = root / "issues" / "shabits"

        import board_migrate
        orig = board_migrate.BOARD_ROOT
        board_migrate.BOARD_ROOT = root
        try:
            bm.migrate_shabits(old_shabits, new_shabits)
        finally:
            board_migrate.BOARD_ROOT = orig

        assert (new_shabits / "history.csv").exists()
        assert "morning-routine" in (new_shabits / "history.csv").read_text()


def test_migrate_shabits_copies_shabits_json():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old_shabits = root / "shabits"
        old_shabits.mkdir()
        (old_shabits / "shabits.json").write_text('[{"id": "test"}]')
        (old_shabits / "charts").mkdir()

        import board_migrate
        orig = board_migrate.BOARD_ROOT
        board_migrate.BOARD_ROOT = root
        try:
            bm.migrate_shabits(old_shabits, root / "issues" / "shabits")
        finally:
            board_migrate.BOARD_ROOT = orig

        dest = root / "issues" / "shabits" / "shabits.json"
        assert dest.exists()
        assert "test" in dest.read_text()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 -m pytest tests/test_board_migrate.py -v
```

Expected: collection error — `scripts/board-migrate` not found

- [ ] **Step 3: Implement board-migrate**

```python
#!/usr/bin/env python3
"""
board-migrate — one-time migration from old flat board to issues/ hierarchy

Old layout: board/{issue}/p0/, p1/, p2/ — individual .md files per task
New layout: board/issues/{group}/{issue}/ — schedule.json + p0.md/p1.md/p2.md/done.md

Usage:
  board-migrate --dry    show what would happen, no changes
  board-migrate          perform migration
"""
import json
import shutil
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

BOARD_ROOT = Path.home() / "Board" / "board"
DRY = "--dry" in sys.argv

ISSUE_MAP = {
    "cv":     ("projects", "cv"),
    "mvg":    ("reading-material", "mvg"),
    "papers": ("reading-material", "papers"),
    "rl":     ("reading-material", "rl"),
}
WORK_ISSUES = ["ai_therapist"]


def _log(msg):
    print(f"  {'[dry] ' if DRY else ''}{msg}")


def _ensure(path):
    if not DRY:
        path.mkdir(parents=True, exist_ok=True)


def _write(path, content):
    if not DRY:
        path.write_text(content)
    _log(f"write {path}")


def _copy(src, dst):
    if not DRY:
        shutil.copy2(str(src), str(dst))
    _log(f"copy {src} → {dst}")


def _move(src, dst):
    if not DRY:
        shutil.move(str(src), str(dst))
    _log(f"move {src} → {dst}")


def _rmdir(path):
    if not DRY:
        shutil.rmtree(path)
    _log(f"remove {path}")


def parse_old_task(path):
    """Return (meta_dict, body_str) from an old frontmatter+body .md file."""
    text = path.read_text()
    meta, body, in_fm, fm_done = {}, [], False, False
    for i, line in enumerate(text.splitlines()):
        if i == 0 and line.strip() == "---":
            in_fm = True
            continue
        if in_fm and line.strip() == "---":
            in_fm, fm_done = False, True
            continue
        if in_fm and ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip("'\"")
        elif fm_done:
            body.append(line)
    return meta, "\n".join(body).strip()


def tasks_from_body(body):
    """Extract checkbox lines from markdown body as task dicts."""
    tasks = []
    for i, line in enumerate(body.splitlines()):
        s = line.strip()
        if s.startswith("- [ ]"):
            tasks.append({"id": f"t{i+1}", "text": s[5:].strip(), "done": False})
        elif s.startswith("- [x]"):
            tasks.append({"id": f"t{i+1}", "text": s[5:].strip(), "done": True})
    return tasks


def migrate_issue(old_path, new_path, issue_name):
    """Convert one old-style issue directory to the new layout."""
    _ensure(new_path)
    _ensure(new_path / "graphs")

    p1_events = []
    old_p1 = old_path / "p1"
    if old_p1.exists():
        for f in sorted(old_p1.glob("*.md")):
            meta, body = parse_old_task(f)
            p1_events.append({
                "id": meta.get("id", f.stem),
                "title": meta.get("summary", f.stem),
                "time_blocks": [],
                "tasks": tasks_from_body(body),
            })

    p0_events = []
    old_p0 = old_path / "p0"
    if old_p0.exists():
        for f in sorted(old_p0.glob("*.md")):
            meta, body = parse_old_task(f)
            p0_events.append({
                "id": meta.get("id", f.stem),
                "title": meta.get("summary", f.stem),
                "date": str(date.today()),
                "time_blocks": [],
                "tasks": tasks_from_body(body),
            })

    schedule = {
        "issue": issue_name,
        "p0": p0_events,
        "p1": p1_events,
        "done": [],
    }
    _write(new_path / "schedule.json", json.dumps(schedule, indent=2) + "\n")

    p2_lines = [f"# {issue_name.upper()}", ""]
    old_p2 = old_path / "p2"
    if old_p2.exists():
        for f in sorted(old_p2.glob("*.md")):
            meta, _ = parse_old_task(f)
            p2_lines.append(f"## {meta.get('summary', f.stem)}")
    _write(new_path / "p2.md", "\n".join(p2_lines) + "\n")

    _write(new_path / "p0.md", f"# {issue_name.upper()}\n")
    _write(new_path / "p1.md", f"# {issue_name.upper()}\n")
    _write(new_path / "done.md", f"# {issue_name.upper()}\n")
    _write(new_path / "history.csv", "date,event_id,event_title,task_id,task_text\n")


def migrate_shabits(old_shabits, new_shabits):
    """Migrate shabits: copy json, move charts→graphs, move done/shabits.csv→history.csv."""
    _ensure(new_shabits)
    _ensure(new_shabits / "graphs")

    sj = old_shabits / "shabits.json"
    if sj.exists():
        _copy(sj, new_shabits / "shabits.json")

    old_charts = old_shabits / "charts"
    if old_charts.exists():
        for f in old_charts.iterdir():
            _move(f, new_shabits / "graphs" / f.name)

    old_csv = BOARD_ROOT / "done" / "shabits.csv"
    if old_csv.exists():
        _move(old_csv, new_shabits / "history.csv")
    else:
        _write(new_shabits / "history.csv", "date,habit_id\n")

    schedule = {"issue": "shabits", "p0": [], "p1": [], "done": []}
    _write(new_shabits / "schedule.json", json.dumps(schedule, indent=2) + "\n")
    _write(new_shabits / "p0.md", "# SHABITS\n")
    _write(new_shabits / "done.md", "# SHABITS\n")


def run():
    issues_root = BOARD_ROOT / "issues"
    for group in ("projects", "reading-material", "work"):
        _ensure(issues_root / group)

    for old_name, (group, new_name) in ISSUE_MAP.items():
        old_path = BOARD_ROOT / old_name
        new_path = issues_root / group / new_name
        if old_path.exists():
            _log(f"Migrating {old_name} → issues/{group}/{new_name}")
            migrate_issue(old_path, new_path, new_name)
        else:
            _log(f"Skip {old_name} (not found)")

    for wname in WORK_ISSUES:
        old_path = BOARD_ROOT / "work" / wname
        new_path = issues_root / "work" / wname
        if old_path.exists():
            _log(f"Migrating work/{wname} → issues/work/{wname}")
            migrate_issue(old_path, new_path, wname)

    old_shabits = BOARD_ROOT / "shabits"
    new_shabits = issues_root / "shabits"
    if old_shabits.exists():
        _log("Migrating shabits → issues/shabits")
        migrate_shabits(old_shabits, new_shabits)

    meditation = BOARD_ROOT / "meditation"
    if meditation.exists():
        _log("Removing meditation/ (already a shabit)")
        _rmdir(meditation)

    if not DRY:
        print("\n  Migration complete.")
        print("  Next: run board-aggregate to rebuild board-level files")


if __name__ == "__main__":
    run()
```

- [ ] **Step 4: Make executable**

```bash
chmod +x scripts/board-migrate
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
python3 -m pytest tests/test_board_migrate.py -v
```

Expected: 11 passed

- [ ] **Step 6: Commit**

```bash
git add scripts/board-migrate tests/test_board_migrate.py
git commit -m "feat: add board-migrate — one-time migration to issues/ hierarchy"
```

---

## Task 5: install.sh — install new scripts and scaffold directory structure

**Files:**
- Modify: `install.sh`

- [ ] **Step 1: Read current install.sh scripts loop**

Open `install.sh` and locate the scripts loop (around line 75):

```bash
for script in shabits shabits-graphs habits-watch board-pages board-watch board-sync p0 groundwork-monitor; do
```

- [ ] **Step 2: Add new scripts to the loop**

Replace that line with:

```bash
for script in shabits shabits-graphs habits-watch board-pages board-watch board-sync board-generate board-aggregate board-migrate p0 groundwork-monitor; do
```

- [ ] **Step 3: Add issues/ directory scaffolding**

After the `mkdir -p` block that creates `"$BOARD_ROOT/shabits/charts"`, add:

```bash
mkdir -p \
    "$BOARD_ROOT/issues/shabits/graphs" \
    "$BOARD_ROOT/issues/projects" \
    "$BOARD_ROOT/issues/reading-material" \
    "$BOARD_ROOT/issues/work"

ok "Board issues/ directories created"
```

- [ ] **Step 4: Run all tests to check nothing regressed**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass (existing + new)

- [ ] **Step 5: Verify install.sh is valid bash**

```bash
bash -n install.sh
```

Expected: no output (syntax OK)

- [ ] **Step 6: Commit**

```bash
git add install.sh
git commit -m "feat: install.sh — add board-generate, board-aggregate, board-migrate + issues/ scaffold"
```

---

## Task 6: Run the migration on the live board

This task is manual — it modifies `~/Board/board/` in place. Run `--dry` first.

- [ ] **Step 1: Preview the migration**

```bash
cd ~/Projects/Groundwork
python3 scripts/board-migrate --dry
```

Expected: lines showing what would be created/moved, no actual changes.

- [ ] **Step 2: Run the migration**

```bash
python3 scripts/board-migrate
```

Expected: `Migration complete.`

- [ ] **Step 3: Verify the new structure**

```bash
find -L ~/Board/board/issues -maxdepth 3 -type d | sort
```

Expected: directories for `issues/shabits/`, `issues/projects/cv/`, `issues/reading-material/mvg`, `issues/reading-material/papers`, `issues/reading-material/rl`, `issues/work/ai_therapist/`

- [ ] **Step 4: Spot-check a schedule.json**

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from board_schema import load_schedule
s = load_schedule('$HOME/Board/board/issues/projects/cv/schedule.json')
print('issue:', s['issue'])
print('p1 events:', len(s['p1']))
print('first p1:', s['p1'][0]['title'] if s['p1'] else 'none')
"
```

Expected: issue name is `cv`, p1 events listed.

- [ ] **Step 5: Run board-generate on each issue**

```bash
for issue in \
    ~/Board/board/issues/projects/cv \
    ~/Board/board/issues/reading-material/mvg \
    ~/Board/board/issues/reading-material/papers \
    ~/Board/board/issues/reading-material/rl \
    ~/Board/board/issues/work/ai_therapist \
    ~/Board/board/issues/shabits; do
    python3 ~/Projects/Groundwork/scripts/board-generate "$issue" && echo "  OK $issue"
done
```

Expected: `OK` for each issue; each directory now has `p0.md`, `p1.md`, `done.md`.

- [ ] **Step 6: Run board-aggregate**

```bash
python3 ~/Projects/Groundwork/scripts/board-aggregate
```

Expected: `Aggregated N issues → ~/Board/board`

- [ ] **Step 7: Verify board-level files**

```bash
head -20 ~/Board/board/p1.md
```

Expected: grouped view of all issues' p1 events with correct headings.

- [ ] **Step 8: Commit**

```bash
cd ~/Projects/Groundwork
git add install.sh
git commit -m "feat: complete board foundation — migration run, all issues on new layout"
```

---

## Full test run

- [ ] **Run all tests**

```bash
python3 -m pytest tests/ -v
```

Expected: all tests pass with 0 failures.
