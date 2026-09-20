# FlipDoctor — developer convenience targets.
# Sole author: Krishita Sanjay Choksi.

PY ?= python3

.PHONY: help sim list test eval figures demo all fap clean

help:
	@echo "FlipDoctor make targets:"
	@echo "  make sim STATE=ir_rx_fail  - run the fault simulator for a state"
	@echo "  make list                  - list simulated fault states"
	@echo "  make test                  - run the pytest suite"
	@echo "  make eval                  - evaluator accuracy metrics + charts"
	@echo "  make figures               - regenerate hero report, certificate, architecture"
	@echo "  make demo                  - regenerate the demo GIF (needs Pillow)"
	@echo "  make all                   - test + eval + figures"
	@echo "  make fap                   - build the Flipper .fap (needs ufbt)"

STATE ?= healthy
sim:
	$(PY) sim/simulate.py --state $(STATE)

list:
	$(PY) sim/simulate.py --list

test:
	$(PY) -m pytest -q

eval:
	$(PY) eval/run_eval.py

figures:
	$(PY) figures/generate_figures.py

demo:
	$(PY) figures/generate_demo.py

all: test eval figures

fap:
	ufbt

clean:
	rm -rf .ufbt dist build __pycache__ */__pycache__ .pytest_cache
