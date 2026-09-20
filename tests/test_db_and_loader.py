"""Thresholds, known-issue signatures, and the readings loader."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.loader import load_readings, report_from_file
from flipdoctor.models import Subsystem
from flipdoctor.thresholds import load_known_issues, load_thresholds, match_known_issue

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_thresholds_load():
    th = load_thresholds()
    assert th["battery"]["voltage_min_v"] < th["battery"]["voltage_max_v"]
    assert "subghz" in th and "nfc" in th


def test_known_issue_matches_ir_dust():
    note = match_known_issue("ir_rx", {"loopback_match_ratio": 0.1, "ir_tx_ok": True})
    assert "dust" in note.lower() or "window" in note.lower()


def test_known_issue_no_match():
    assert match_known_issue("ir_rx", {"loopback_match_ratio": 0.95, "ir_tx_ok": True}) == ""


def test_loader_reads_sample():
    path = os.path.join(_ROOT, "data", "real_logs", "device_sample_readings.json")
    readings = load_readings(path)
    assert Subsystem.BATTERY in readings
    rep = report_from_file(path)
    assert len(rep.results) >= 1
