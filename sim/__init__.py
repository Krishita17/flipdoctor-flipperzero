"""Fault-state result simulator for FlipDoctor.

Produces raw subsystem readings for a healthy device and for a catalogue of
faulty states, so the evaluator, report generator, and eval pipeline can be
developed and validated without physically breaking hardware.
"""

from .simulate import (
    FAULT_STATES,
    GROUND_TRUTH,
    simulate_readings,
    simulate_report,
)

__all__ = ["FAULT_STATES", "GROUND_TRUTH", "simulate_readings", "simulate_report"]
