# Prior art & honest positioning

FlipDoctor did **not** invent hardware testing for the Flipper Zero. This
document credits the existing work and states plainly what is and isn't novel
here. Overclaiming novelty would undermine the one thing a diagnostic tool
must have: trust.

## What already exists

- **Firmware low-level checks.** The official Flipper Zero firmware includes
  low-level bring-up and self-check paths for hardware components (for example
  chip-presence/SPI checks for the CC1101 sub-GHz transceiver and the ST25R
  NFC front-end during driver init, SD card mount/verify, and battery/fuel-gauge
  readouts via the power HAL). These are not surfaced to owners as a single
  "is my device healthy?" verdict.
- **Single-feature apps and debug tools.** Individual apps and developer/debug
  tools exercise individual subsystems (sub-GHz frequency analyzers, NFC
  readers, IR universal remotes, GPIO tools). Each proves one feature works in
  the course of using it, but none is a *diagnostic* with an interpretable
  pass/fail intent.
- **General POST / self-test design.** Power-on self-test (POST) and built-in
  self-test (BIST) are long-established patterns in computing hardware.
  FlipDoctor applies these established ideas to the Flipper; it does not claim
  to originate them.

## What FlipDoctor contributes

1. **A unified, one-tap diagnostic suite** — every subsystem exercised in one
   coherent flow producing a single overall health verdict. This packaging did
   not exist for the Flipper.
2. **Interpretable results** — not raw readings but `PASS / FAIL / WARN /
   INCONCLUSIVE` with a confidence level and plain-language "what this means /
   what to try" guidance.
3. **A used-buyer verification mode** — a purpose-built pre-purchase flow that
   exports a shareable "health certificate."
4. **A repeatable baseline** — save a report and re-run later to detect
   degradation over time.
5. **An explicit honesty layer** — every test labeled self-contained vs.
   stronger-with-accessory, and a deliberate refusal to emit false certainty
   (`RESPONDS` and `INCONCLUSIVE` are first-class outcomes).

## What FlipDoctor does *not* claim

- It does not claim to be the first to test Flipper hardware.
- It does not claim a `RESPONDS`/`PASS` self-test fully validates a subsystem;
  see [`threat_model.md`](threat_model.md) for the limits.
- It does not replace lab equipment or a full hardware teardown.

## Sources to cite in the repo

When wiring the on-device tests to real hardware, ground each test in the
documented behavior of the relevant component and cite it here:

- Flipper Zero hardware overview and pinout (official docs).
- Sub-GHz: Texas Instruments CC1101 datasheet.
- NFC: STMicroelectronics ST25R3916 datasheet.
- Firmware HAL / `furi_hal_*` source for battery, SD, GPIO, IR access.
- ufbt (micro Flipper Build Tool) documentation for building the `.fap`.

*Maintained solely by Krishita Sanjay Choksi.*
