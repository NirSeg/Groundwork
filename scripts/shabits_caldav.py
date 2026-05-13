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
