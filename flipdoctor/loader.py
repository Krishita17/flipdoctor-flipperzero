"""Load raw readings (real or simulated) and produce a report.

Readings files are JSON mapping subsystem value -> readings dict, i.e. the same
shape the fault simulator emits with ``--readings`` and the shape the on-device
app writes when you "Export raw" to SD. This lets the author feed logs captured
from their own Flipper through the exact same evaluator/report code path.

CLI:
    python3 -m flipdoctor.loader data/real_logs/device_A.json
    python3 -m flipdoctor.loader data/real_logs/device_A.json --json
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from .evaluate import evaluate_all
from .models import Report, Subsystem
from .report import build_report, render_text, to_json


def load_readings(path: str) -> Dict[Subsystem, Dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    out: Dict[Subsystem, Dict[str, Any]] = {}
    valid = {s.value: s for s in Subsystem}
    for key, vals in raw.items():
        if key not in valid:
            raise ValueError(f"unknown subsystem {key!r} in {path}")
        out[valid[key]] = vals
    return out


def report_from_file(path: str, *, mode: str = "full", firmware: str = "unknown") -> Report:
    readings = load_readings(path)
    results = evaluate_all(readings)
    return build_report(results, firmware=firmware, mode=mode)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Evaluate a FlipDoctor readings file")
    ap.add_argument("path", help="path to a readings JSON file")
    ap.add_argument("--json", action="store_true", help="emit report as JSON")
    ap.add_argument("--mode", default="full")
    ap.add_argument("--firmware", default="unknown")
    args = ap.parse_args(argv)
    report = report_from_file(args.path, mode=args.mode, firmware=args.firmware)
    print(to_json(report) if args.json else render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
