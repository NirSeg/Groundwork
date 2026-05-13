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
