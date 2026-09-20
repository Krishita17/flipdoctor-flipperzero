"""Evaluator accuracy pipeline.

Runs the evaluator against every simulated device state across many seeds and
measures, per subsystem:

* precision / recall / F1 of "fault detected"
* the false-alarm rate on the healthy state (a diagnostic that cries wolf is
  useless), and
* honesty-labeling coverage (self-contained vs. needs-accessory).

Outputs a metrics JSON to ``eval/metrics.json`` and, if matplotlib is
available, charts to ``figures/``. Runs from a clean clone; no hardware.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flipdoctor.evaluate import evaluate_all  # noqa: E402
from flipdoctor.models import Subsystem  # noqa: E402
from sim.simulate import FAULT_STATES, GROUND_TRUTH, simulate_readings  # noqa: E402

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIG = os.path.join(_ROOT, "figures")

N_SEEDS = 50


def _confusion() -> Dict[Subsystem, Dict[str, int]]:
    """Per-subsystem confusion counts over all states x seeds.

    A subsystem is 'predicted faulty' when its status is not healthy
    (not PASS/RESPONDS). It is 'actually faulty' per GROUND_TRUTH for the state.
    """
    conf = {s: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for s in Subsystem}
    for state in FAULT_STATES:
        truth = GROUND_TRUTH[state]
        for seed in range(N_SEEDS):
            readings = simulate_readings(state, seed=seed)
            results = {r.subsystem: r for r in evaluate_all(readings)}
            for sub, res in results.items():
                predicted_fault = not res.status.is_healthy
                actual_fault = sub in truth
                if predicted_fault and actual_fault:
                    conf[sub]["tp"] += 1
                elif predicted_fault and not actual_fault:
                    conf[sub]["fp"] += 1
                elif not predicted_fault and actual_fault:
                    conf[sub]["fn"] += 1
                else:
                    conf[sub]["tn"] += 1
    return conf


def _prf(c: Dict[str, int]) -> Dict[str, float]:
    tp, fp, fn = c["tp"], c["fp"], c["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def _false_alarm_rate() -> float:
    """Fraction of healthy runs that produced ANY non-healthy subsystem verdict.

    INCONCLUSIVE is not counted as a false alarm (it is honest uncertainty, not
    a wolf-cry); only WARN/FAIL on a truly healthy subsystem count.
    """
    from flipdoctor.models import Status

    bad_runs = 0
    for seed in range(N_SEEDS):
        readings = simulate_readings("healthy", seed=seed)
        results = evaluate_all(readings)
        if any(r.status in (Status.WARN, Status.FAIL) for r in results):
            bad_runs += 1
    return bad_runs / N_SEEDS


def _honesty_coverage() -> Dict[str, int]:
    readings = simulate_readings("healthy", seed=0)
    results = evaluate_all(readings)
    self_contained = sum(1 for r in results if not r.needs_accessory)
    needs_acc = sum(1 for r in results if r.needs_accessory)
    labeled = sum(1 for r in results if r.confidence is not None)
    return {
        "total": len(results),
        "self_contained": self_contained,
        "needs_accessory": needs_acc,
        "confidence_labeled": labeled,
    }


def compute_metrics() -> Dict:
    conf = _confusion()
    per_sub = {}
    for sub in Subsystem:
        c = conf[sub]
        if c["tp"] + c["fn"] == 0 and c["fp"] == 0:
            continue  # subsystem never exercised as a fault; skip from PRF table
        per_sub[sub.value] = {**_prf(c), **c, "label": sub.label}
    return {
        "n_seeds": N_SEEDS,
        "per_subsystem": per_sub,
        "false_alarm_rate_healthy": _false_alarm_rate(),
        "honesty_coverage": _honesty_coverage(),
    }


def _plot(metrics: Dict) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        print(f"[eval] matplotlib unavailable ({exc}); skipping charts.")
        return

    os.makedirs(_FIG, exist_ok=True)
    per = metrics["per_subsystem"]
    labels = [v["label"] for v in per.values()]
    precision = [v["precision"] for v in per.values()]
    recall = [v["recall"] for v in per.values()]

    # Chart 1: precision/recall per subsystem
    x = range(len(labels))
    width = 0.38
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar([i - width / 2 for i in x], precision, width, label="Precision", color="#2f855a")
    ax.bar([i + width / 2 for i in x], recall, width, label="Recall", color="#2b6cb0")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("FlipDoctor evaluator accuracy per subsystem (simulated faults)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(_FIG, "evaluator_accuracy.png"), dpi=140)
    plt.close(fig)

    # Chart 2: coverage / confidence map
    hc = metrics["honesty_coverage"]
    fig, ax = plt.subplots(figsize=(7, 4))
    cats = ["Self-contained", "Needs accessory"]
    vals = [hc["self_contained"], hc["needs_accessory"]]
    ax.bar(cats, vals, color=["#2f855a", "#b7791f"])
    ax.set_title(f"Test coverage map ({hc['total']} subsystems, all confidence-labeled)")
    ax.set_ylabel("Subsystems")
    for i, v in enumerate(vals):
        ax.text(i, v + 0.05, str(v), ha="center")
    fig.tight_layout()
    fig.savefig(os.path.join(_FIG, "coverage_map.png"), dpi=140)
    plt.close(fig)
    print(f"[eval] wrote charts to {_FIG}/")


def main() -> int:
    metrics = compute_metrics()
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metrics.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"[eval] wrote {out}")

    print("\nPer-subsystem accuracy (fault detection):")
    print(f"{'subsystem':<24}{'precision':>10}{'recall':>10}{'f1':>8}")
    for v in metrics["per_subsystem"].values():
        print(f"{v['label']:<24}{v['precision']:>10.2f}{v['recall']:>10.2f}{v['f1']:>8.2f}")
    print(f"\nFalse-alarm rate on healthy device: "
          f"{metrics['false_alarm_rate_healthy']:.1%}")
    hc = metrics["honesty_coverage"]
    print(f"Honesty coverage: {hc['confidence_labeled']}/{hc['total']} confidence-labeled, "
          f"{hc['needs_accessory']} flagged 'needs accessory'.")

    _plot(metrics)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
