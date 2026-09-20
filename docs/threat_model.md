# Threat model — really an accuracy & honesty model

FlipDoctor has no offensive capability. It tests the owner's own device's own
subsystems; there is no attack surface and no target other than the Flipper in
your hand. So the "threat" that matters is **misdiagnosis**: a wrong verdict
that costs someone a device, money, or trust. This document is the guardrail
against that.

## Scope

- **In scope:** on-device self-diagnostics of the user's own Flipper Zero
  (sub-GHz, NFC, IR TX/RX, GPIO, SD, battery, buttons/display/LED/vibro), an
  interpretable report, a used-buyer verification mode, and baseline compare.
- **Out of scope:** anything offensive, any test of *another* person's device
  without their consent, and any claim of certification beyond what the tests
  actually measure.

## The real risks and how we mitigate them

### 1. False FAIL (telling someone healthy hardware is broken)
A false "your NFC coil is dead" could make an owner pay for needless repair or
walk away from a good used purchase.

**Mitigations**
- Prefer `INCONCLUSIVE` over `FAIL` whenever evidence is insufficient, with a
  concrete next step.
- Environmental confounders (RF noise, ambient IR, angle) are called out in the
  guidance before hardware failure is suggested.
- The eval pipeline measures the **false-alarm rate on a healthy device** and
  the target is 0% (see `eval/run_eval.py`).

### 2. False PASS (certifying broken hardware as fine)
Worse for the used-buyer use case: a false "all healthy" could help a bad unit
get sold.

**Mitigations**
- `RESPONDS` is distinct from `PASS`. A self-test that can only prove "alive"
  never reports `PASS`.
- Tests that need an accessory for a definitive result are labeled
  `needs accessory`; the used-buyer flow encourages running the stronger GPIO
  jumper check.
- The certificate explicitly states it reflects the tests run at that moment
  and is **evidence, not a lifetime guarantee**.

### 3. Overclaiming what a test proves
"NFC field detected" does not mean every card will read.

**Mitigations**
- Every result carries a plain-language statement of what it does and does not
  prove.
- Confidence levels (`high/medium/low`) are attached to every verdict.

### 4. Destructive advice
A diagnostic must never recommend an action that could damage the device or
lose data without warning.

**Mitigations**
- Guidance is limited to safe, reversible steps (reboot, reseat, retry in a
  different environment, back up before replacing a card).
- The SD write/read test uses a scratch file and never touches user data.

## Limits (documented honestly)

- **Self-tests have ceilings.** Some subsystems can only be verified as
  "alive/responds" on-device alone. Full validation of GPIO and IR RX is
  stronger with a cheap accessory (loopback jumper / known IR target).
- **Interactive tests depend on the user.** Buttons/display/LED/vibro rely on
  the owner confirming what they see and feel.
- **A certificate is a snapshot.** It does not predict future reliability.
- **Thresholds are calibrated, not universal.** They are grounded in documented
  hardware behavior and the author's device; community-contributed thresholds
  improve them over time.

## Used-buyer mode caveat

The health certificate is designed to be shared between a seller and a buyer.
It is strong, structured evidence about the state of the device at test time.
It is **not** an absolute guarantee, cannot detect intermittent faults that did
not occur during testing, and should complement — not replace — a buyer's own
inspection.

*Maintained solely by Krishita Sanjay Choksi.*
