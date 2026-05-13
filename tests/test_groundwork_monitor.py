"""Tests for groundwork-monitor datetime parsing (bug: val[:19] too short)."""

from datetime import datetime
import pytest


def parse_systemd_timestamp(val):
    """Extracted from check_sync_freshness — the thing under test."""
    return datetime.strptime(val[:19], "%a %Y-%m-%d %H:%M:%S")


def test_systemd_timestamp_parses_correctly():
    # systemctl --user show board-sync.timer --property=LastTriggerUSec produces:
    # "Tue 2026-05-12 15:30:00 IST"  (23 chars before timezone)
    val = "Tue 2026-05-12 15:30:00 IST"
    dt = parse_systemd_timestamp(val)
    assert dt.year == 2026
    assert dt.month == 5
    assert dt.day == 12
    assert dt.hour == 15
    assert dt.minute == 30


def test_systemd_timestamp_two_digit_minutes():
    val = "Mon 2026-01-05 09:05:00 UTC"
    dt = parse_systemd_timestamp(val)
    assert dt.hour == 9
    assert dt.minute == 5
