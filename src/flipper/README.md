# On-device Flipper application (C)

This is the `.fap` that runs on the Flipper Zero. It mirrors the portable
Python core (`../../flipdoctor/`) so the on-device verdicts match what the
fault simulator and eval pipeline validate off-device.

```
src/flipper/
├── flipdoctor.h / .c    # data model, entry point, GUI shell, shared helpers
├── orchestrator/        # sequences tests for a mode, collects readings, evaluates
├── tests/               # HAL-backed readings collectors (one path per subsystem)
├── evaluate/            # raw readings -> honest verdict (mirrors evaluate.py)
├── report/              # overall verdict, on-screen render, SD export
├── modes/               # full / quick / used-buyer / single subsystem sets
└── flipdoctor_icon.png  # 10x10 app icon
```

## Build

```bash
python3 -m pip install --upgrade ufbt
ufbt            # build flipdoctor.fap
ufbt launch     # build + upload + run on a connected Flipper
```

## HAL notes (honest)

`tests/tests.c` wires **battery** and **SD** to stable HAL/record APIs and
performs a real scratch write/read for SD. The **sub-GHz / NFC / IR / GPIO**
collectors expose the exact readings the evaluator needs and mark, with
`TODO(hal)`, the one or two probe/capture calls that must be confirmed against
the target firmware version's HAL. Where a reading can't be obtained, the
collector leaves values that the evaluator turns into `INCONCLUSIVE` rather than
a false `PASS`/`FAIL` — consistent with the project's honesty layer.

The verdict logic in `evaluate/evaluate.c` uses the same thresholds as
`db/thresholds.json` and the same rules as the Python evaluator, which is the
component covered by the automated tests and the accuracy eval.
