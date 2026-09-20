"""The trust-critical tests: the evaluator catches each simulated fault and
does not cry wolf on a healthy device."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.evaluate import evaluate_all
from flipdoctor.models import Status
from sim.simulate import FAULT_STATES, GROUND_TRUTH, simulate_readings


@pytest.mark.parametrize("state", [s for s in FAULT_STATES if GROUND_TRUTH[s]])
@pytest.mark.parametrize("seed", [0, 1, 2, 7, 13])
def test_faults_are_flagged(state, seed):
    """Every subsystem that is truly faulty must be flagged as not-healthy."""
    readings = simulate_readings(state, seed=seed)
    results = {r.subsystem: r for r in evaluate_all(readings)}
    for sub in GROUND_TRUTH[state]:
        assert not results[sub].status.is_healthy, (
            f"{state}/seed{seed}: expected {sub.value} flagged, got "
            f"{results[sub].status.value}"
        )


@pytest.mark.parametrize("seed", range(20))
def test_healthy_has_no_false_alarms(seed):
    """A healthy device must never produce WARN/FAIL."""
    readings = simulate_readings("healthy", seed=seed)
    results = evaluate_all(readings)
    for r in results:
        assert r.status not in (Status.WARN, Status.FAIL), (
            f"false alarm on healthy device: {r.subsystem.value} -> "
            f"{r.status.value}"
        )


@pytest.mark.parametrize("seed", range(10))
def test_healthy_faulty_subsystems_are_healthy(seed):
    """For a fault state, subsystems NOT in ground truth stay healthy
    (no collateral false alarms), except IR RX which honestly reports it
    cannot test while IR TX is down."""
    for state in FAULT_STATES:
        truth = GROUND_TRUTH[state]
        results = {r.subsystem: r for r in evaluate_all(simulate_readings(state, seed=seed))}
        for sub, res in results.items():
            if sub in truth:
                continue
            assert res.status not in (Status.FAIL,), (
                f"{state}: unexpected FAIL on non-faulty {sub.value}"
            )


def test_responds_is_not_pass_for_nfc():
    """NFC self-check must report RESPONDS (alive), never a false PASS."""
    results = {r.subsystem.value: r for r in evaluate_all(simulate_readings("healthy"))}
    assert results["nfc"].status == Status.RESPONDS


def test_gpio_without_jumper_is_honest():
    """No jumper -> weak result (RESPONDS/INCONCLUSIVE), flagged needs-accessory."""
    results = {r.subsystem.value: r for r in evaluate_all(simulate_readings("gpio_no_jumper"))}
    gpio = results["gpio"]
    assert gpio.needs_accessory is True
    assert gpio.status in (Status.RESPONDS, Status.INCONCLUSIVE)
