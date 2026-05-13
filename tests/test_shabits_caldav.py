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


def test_mark_today_complete_updates_status_in_ics():
    from shabits_caldav import make_daily_vtodo, vtodo_filename, mark_today_complete
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        path = tasks_dir / vtodo_filename("morning-routine", today)
        path.write_text(make_daily_vtodo(habit, today))
        assert "STATUS:NEEDS-ACTION" in path.read_text()

        mark_today_complete(habit, tasks_dir=tasks_dir, today=today)

        content = path.read_text()
        assert "STATUS:COMPLETED" in content
        assert "STATUS:NEEDS-ACTION" not in content


def test_mark_today_complete_creates_vtodo_if_missing():
    from shabits_caldav import vtodo_filename, mark_today_complete
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        mark_today_complete(habit, tasks_dir=tasks_dir, today=today)
        path = tasks_dir / vtodo_filename("morning-routine", today)
        assert path.exists()
        assert "STATUS:COMPLETED" in path.read_text()


def test_sync_completions_reads_phone_completion_into_csv():
    from shabits_caldav import make_daily_vtodo, sync_completions, vtodo_filename
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        csv_file  = Path(tmp) / "shabits.csv"
        csv_file.write_text("date,habit_id\n")

        path = tasks_dir / vtodo_filename("morning-routine", today)
        path.write_text(make_daily_vtodo(habit, today).replace(
            "STATUS:NEEDS-ACTION", "STATUS:COMPLETED"
        ))

        added = sync_completions([habit], tasks_dir=tasks_dir, csv_file=csv_file)

        assert added == 1
        rows = csv_file.read_text().splitlines()
        assert any(str(today) in r and "morning-routine" in r for r in rows)


def test_sync_completions_skips_already_in_csv():
    from shabits_caldav import make_daily_vtodo, sync_completions, vtodo_filename
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        csv_file  = Path(tmp) / "shabits.csv"
        csv_file.write_text(f"date,habit_id\n{today},morning-routine\n")

        path = tasks_dir / vtodo_filename("morning-routine", today)
        path.write_text(make_daily_vtodo(habit, today).replace(
            "STATUS:NEEDS-ACTION", "STATUS:COMPLETED"
        ))

        added = sync_completions([habit], tasks_dir=tasks_dir, csv_file=csv_file)
        assert added == 0


def test_sync_completions_ignores_needs_action():
    from shabits_caldav import make_daily_vtodo, sync_completions, vtodo_filename
    today = date.today()
    habit = _make_habit("morning-routine", "Morning Routine")
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        csv_file  = Path(tmp) / "shabits.csv"
        csv_file.write_text("date,habit_id\n")

        path = tasks_dir / vtodo_filename("morning-routine", today)
        path.write_text(make_daily_vtodo(habit, today))

        added = sync_completions([habit], tasks_dir=tasks_dir, csv_file=csv_file)
        assert added == 0


def test_cleanup_deletes_vtodos_older_than_cutoff():
    from shabits_caldav import vtodo_filename, cleanup
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir = Path(tmp)
        old_date  = date.today() - timedelta(days=4)
        old_path  = tasks_dir / vtodo_filename("morning-routine", old_date)
        old_path.write_text("old content")

        removed = cleanup(days=3, tasks_dir=tasks_dir)

        assert removed == 1
        assert not old_path.exists()


def test_cleanup_keeps_vtodos_within_cutoff():
    from shabits_caldav import vtodo_filename, cleanup
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir   = Path(tmp)
        recent_date = date.today() - timedelta(days=2)
        recent_path = tasks_dir / vtodo_filename("morning-routine", recent_date)
        recent_path.write_text("recent content")

        removed = cleanup(days=3, tasks_dir=tasks_dir)

        assert removed == 0
        assert recent_path.exists()


def test_cleanup_ignores_non_habit_ics_files():
    from shabits_caldav import cleanup
    with tempfile.TemporaryDirectory() as tmp:
        tasks_dir  = Path(tmp)
        board_file = tasks_dir / "board-p0-some-task.ics"
        board_file.write_text("board task")

        cleanup(days=3, tasks_dir=tasks_dir)

        assert board_file.exists()
