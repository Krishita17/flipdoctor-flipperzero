"""Report generation, JSON round-trip, modes, and baseline compare."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.evaluate import evaluate_all
from flipdoctor.models import Status, Subsystem
from flipdoctor.modes import compare_baseline, subsystems_for_mode, QUICK_SUBSYSTEMS
from flipdoctor.report import build_report, render_certificate, render_text, to_json
from sim.simulate import simulate_readings, simulate_report


def _report(state, seed=0, mode="full"):
    return build_report(evaluate_all(simulate_readings(state, seed=seed)), mode=mode)


def test_overall_fail_when_any_fail():
    rep = _report("nfc_dead")
    assert rep.overall == Status.FAIL
    assert rep.overall_label == "FAULT DETECTED"


def test_overall_warn_when_only_warn():
    rep = _report("aged_battery")
    assert rep.overall == Status.WARN


def test_overall_pass_when_healthy():
    rep = _report("healthy")
    assert rep.overall in (Status.PASS,)
    assert rep.overall_label == "HEALTHY"


def test_report_json_roundtrip():
    rep = _report("multi_fault")
    d = json.loads(to_json(rep))
    assert d["overall"] == "FAIL"
    assert len(d["results"]) == len(list(Subsystem))
    assert "report_id" in d and d["report_id"].startswith("FD-")


def test_report_id_is_deterministic():
    a = simulate_report("healthy", seed=1)
    b = simulate_report("healthy", seed=1)
    assert a.report_id == b.report_id


def test_render_text_mentions_honesty():
    txt = render_text(_report("healthy"))
    assert "RESPONDS" in txt
    assert "INCONCLUSIVE" in txt


def test_certificate_contains_verdict():
    cert = render_certificate(_report("healthy", mode="used_buyer"))
    assert "HEALTH CERTIFICATE" in cert
    assert "VERDICT" in cert


def test_modes_select_subsystems():
    assert set(subsystems_for_mode("quick")) == set(QUICK_SUBSYSTEMS)
    assert len(subsystems_for_mode("full")) == len(list(Subsystem))
    assert subsystems_for_mode("single", Subsystem.SD) == [Subsystem.SD]


def test_baseline_detects_degradation():
    baseline = _report("healthy")
    current = _report("nfc_dead")
    diff = compare_baseline(baseline, current)
    assert diff["degraded"] >= 1
    assert any(c["subsystem"] == "nfc" for c in diff["changes"])


def test_baseline_stable_when_same():
    baseline = _report("healthy", seed=1)
    current = _report("healthy", seed=2)
    diff = compare_baseline(baseline, current)
    assert diff["degraded"] == 0
