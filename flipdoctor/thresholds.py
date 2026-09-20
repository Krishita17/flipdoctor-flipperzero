"""Threshold loading for the evaluator.

Thresholds live in ``db/thresholds.json`` so they can be tuned and
community-contributed without touching code. Known-issue signatures live in
``db/known_issues.json``.
"""

from __future__ import annotations

import functools
import json
import os
from typing import Any, Dict, List

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db")


@functools.lru_cache(maxsize=1)
def load_thresholds() -> Dict[str, Any]:
    with open(os.path.join(_DB_DIR, "thresholds.json"), encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def load_known_issues() -> List[Dict[str, Any]]:
    with open(os.path.join(_DB_DIR, "known_issues.json"), encoding="utf-8") as fh:
        return json.load(fh).get("signatures", [])


def match_known_issue(subsystem: str, readings: Dict[str, Any]) -> str:
    """Return a known-issue note if the readings match a signature, else ''."""
    for sig in load_known_issues():
        if sig.get("subsystem") != subsystem:
            continue
        when = sig.get("when", {})
        if _matches(when, readings):
            return sig.get("note", "")
    return ""


def _matches(when: Dict[str, Any], readings: Dict[str, Any]) -> bool:
    for key, expected in when.items():
        if key.endswith("_below"):
            base = key[: -len("_below")]
            val = readings.get(base)
            if val is None or not val < expected:
                return False
        elif isinstance(expected, bool):
            if bool(readings.get(key)) is not expected:
                return False
        else:
            if readings.get(key) != expected:
                return False
    return True
