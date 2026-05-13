import json
from pathlib import Path


def test_shabits_json_has_due_time_field():
    example = Path("config/shabits.json.example")
    habits = json.loads(example.read_text())
    assert all("due_time" in h for h in habits), "all habits must have due_time"


def test_shabits_json_has_calendar_block_field():
    example = Path("config/shabits.json.example")
    habits = json.loads(example.read_text())
    assert all("calendar_block" in h for h in habits), "all habits must have calendar_block"


import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "scripts")

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _make_habit(id_, name, days=None):
    return {
        "id": id_,
        "name": name,
        "days": days or DAY_NAMES,
        "due_time": "070000",
        "calendar_block": {"start": "06:00", "end": "07:00"},
    }


def test_generate_today_creates_vtodo_for_scheduled_habit():
    from shabits_caldav import generate_today, vtodo_filename
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        generate_today([habit], tasks_dir=tasks_dir, today=today)
        path = tasks_dir / vtodo_filename("morning-routine", today)
        assert path.exists()
        content = path.read_text()
        assert "STATUS:NEEDS-ACTION" in content
        assert "SUMMARY:Morning Routine" in content
        assert today.strftime("%Y%m%d") in content


def test_generate_today_skips_existing_vtodo():
    from shabits_caldav import generate_today, vtodo_filename
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        path = tasks_dir / vtodo_filename("morning-routine", today)
        path.write_text("existing content")
        generate_today([habit], tasks_dir=tasks_dir, today=today)
        assert path.read_text() == "existing content"


def test_generate_today_skips_unscheduled_habit():
    from shabits_caldav import generate_today, vtodo_filename
    today = date.today()
    other_days = [d for d in DAY_NAMES if d != DAY_NAMES[today.weekday()]]
    habit = _make_habit("morning-routine", "Morning Routine", days=other_days)
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        generate_today([habit], tasks_dir=tasks_dir, today=today)
        path = tasks_dir / vtodo_filename("morning-routine", today)
        assert not path.exists()
