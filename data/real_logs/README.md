# Real-device diagnostic logs

Small, de-identified readings captured from the author's own Flipper Zero,
committed as samples. Each file is a JSON map of `subsystem -> readings` — the
same shape the fault simulator emits (`sim/simulate.py --readings`) and the
on-device app writes with **Export raw** to SD.

Run any of them through the exact same evaluator/report code path:

```bash
python3 -m flipdoctor.loader data/real_logs/device_sample_readings.json
```

Only small samples live here by design. These logs contain no personal data —
they are hardware readings only (voltages, chip ids, loopback ratios).
Contributions of real readings (especially edge cases) are welcome; see the
main README.
