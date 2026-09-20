/*
 * FlipDoctor — result evaluator (on-device).
 * Mirrors the validated Python evaluator in ../../flipdoctor/evaluate.py.
 * Sole author: Krishita Sanjay Choksi.
 */
#pragma once

#include "../flipdoctor.h"

/* Turn raw readings into an honest verdict + confidence for one subsystem. */
FdResult fd_evaluate(FdSubsystem sub, const FdReadings* r);
