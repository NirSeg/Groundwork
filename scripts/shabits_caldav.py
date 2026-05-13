#!/usr/bin/env python3
"""
shabits-caldav — CalDAV sync for shabits

Usage:
  shabits-caldav run       generate + sync completions + cleanup + vdirsyncer
  shabits-caldav generate  create today's VTODOs for scheduled habits
  shabits-caldav sync      read COMPLETED ICS → update shabits.csv + vdirsyncer
  shabits-caldav cleanup   delete VTODOs older than N days (default 3)
"""

import csv
import json
import subprocess
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

SHABITS_DIR  = Path.home() / "Board" / "board" / "shabits"
JSON_FILE    = SHABITS_DIR / "shabits.json"
CSV_FILE     = Path.home() / "Board" / "board" / "done" / "shabits.csv"
TASKS_DIR    = Path.home() / ".local" / "share" / "vdirsyncer" / "tasks" / "tasks"
TZID         = "Asia/Jerusalem"
CLEANUP_DAYS = 3
DAY_NAMES    = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def load_habits():
    return json.loads(JSON_FILE.read_text())


def vtodo_filename(habit_id, d):
    return f"habit-{habit_id}-{d}.ics"


def make_daily_vtodo(habit, d):
    uid      = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"habit-{habit['id']}-{d}"))
    now_str  = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    due_time = habit.get("due_time", "080000")
    return "\r\n".join([
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//groundwork//shabits//EN",
        "BEGIN:VTODO",
        f"UID:{uid}",
        f"DTSTAMP:{now_str}",
        f"SUMMARY:{habit['name']}",
        f"DUE;TZID={TZID}:{d.strftime('%Y%m%d')}T{due_time}",
        "CATEGORIES:system-habit",
        "STATUS:NEEDS-ACTION",
        "END:VTODO",
        "END:VCALENDAR",
        "",
    ])


def generate_today(habits, tasks_dir=None, today=None):
    tasks_dir = Path(tasks_dir) if tasks_dir else TASKS_DIR
    today     = today or date.today()
    tasks_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for habit in habits:
        if DAY_NAMES[today.weekday()] not in habit["days"]:
            continue
        path = tasks_dir / vtodo_filename(habit["id"], today)
        if path.exists():
            continue
        path.write_text(make_daily_vtodo(habit, today))
        created += 1
    return created


def mark_today_complete(habit, tasks_dir=None, today=None):
    tasks_dir = Path(tasks_dir) if tasks_dir else TASKS_DIR
    today     = today or date.today()
    path      = tasks_dir / vtodo_filename(habit["id"], today)
    if not path.exists():
        path.write_text(make_daily_vtodo(habit, today))
    lines = []
    for line in path.read_text().splitlines():
        lines.append("STATUS:COMPLETED" if line.startswith("STATUS:") else line)
    path.write_text("\r\n".join(lines))


def _append_done(habit_id, date_str, csv_file):
    csv_file = Path(csv_file)
    write_header = not csv_file.exists()
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_file, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["date", "habit_id"])
        w.writerow([date_str, habit_id])


def sync_completions(habits, tasks_dir=None, csv_file=None):
    tasks_dir = Path(tasks_dir) if tasks_dir else TASKS_DIR
    csv_file  = Path(csv_file)  if csv_file  else CSV_FILE

    existing = set()
    if csv_file.exists():
        with open(csv_file, newline="") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    existing.add((row[0].strip(), row[1].strip()))

    habit_ids = {h["id"] for h in habits}
    added = 0

    for ics_path in sorted(tasks_dir.glob("habit-*.ics")):
        stem     = ics_path.stem      # habit-morning-routine-2026-05-13
        date_str = stem[-10:]          # 2026-05-13
        habit_id = stem[6:-11]         # morning-routine

        if habit_id not in habit_ids:
            continue
        try:
            date.fromisoformat(date_str)
        except ValueError:
            continue
        if "STATUS:COMPLETED" not in ics_path.read_text():
            continue
        if (date_str, habit_id) in existing:
            continue

        _append_done(habit_id, date_str, csv_file)
        existing.add((date_str, habit_id))
        added += 1

    return added


def cleanup(days=CLEANUP_DAYS, tasks_dir=None):
    tasks_dir = Path(tasks_dir) if tasks_dir else TASKS_DIR
    cutoff    = date.today() - timedelta(days=days)
    removed   = 0
    for ics_path in tasks_dir.glob("habit-*.ics"):
        stem     = ics_path.stem
        date_str = stem[-10:]
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            continue
        if d < cutoff:
            ics_path.unlink()
            removed += 1
    return removed


def cmd_run():
    habits = load_habits()
    n = generate_today(habits)
    print(f"  generated {n} VTODOs for today")
    subprocess.run(["vdirsyncer", "sync", "nextcloud_tasks"], capture_output=True)
    n = sync_completions(habits)
    print(f"  synced {n} phone completions → shabits.csv")
    n = cleanup()
    print(f"  cleaned up {n} old VTODOs")
    subprocess.run(["vdirsyncer", "sync", "nextcloud_tasks"], capture_output=True)


def cmd_mark_done(habit_id):
    habits = load_habits()
    habit  = next((h for h in habits if h["id"] == habit_id), None)
    if not habit:
        print(f"  Unknown habit: {habit_id}", file=sys.stderr)
        sys.exit(1)
    mark_today_complete(habit)


def main():
    args = sys.argv[1:]
    if not args or args[0] == "run":
        cmd_run()
    elif args[0] == "generate":
        habits = load_habits()
        n = generate_today(habits)
        print(f"  generated {n} VTODOs")
    elif args[0] == "sync":
        habits = load_habits()
        subprocess.run(["vdirsyncer", "sync", "nextcloud_tasks"], capture_output=True)
        n = sync_completions(habits)
        print(f"  synced {n} phone completions")
    elif args[0] == "cleanup":
        n = cleanup()
        print(f"  cleaned up {n} old VTODOs")
    elif args[0] == "mark-done" and len(args) == 2:
        cmd_mark_done(args[1])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
