---
phase: 03-timing-loop
plan: 01
subsystem: timing
tags: [python, math.ceil, nmea, timing, tdd, subprocess]

# Dependency graph
requires:
  - phase: 02-cli-shell-and-logging
    provides: main() loop, --dry-run flag, parse_args(), setup_logging()
provides:
  - sleep_until_next_second() deadline-based helper using math.ceil(time.time())
  - Corrected main() loop: sleep first, then capture datetime.now(timezone.utc)
  - tests/test_timing.py with 6 tests covering TIME-01, TIME-02, TIME-03
affects: [04-signal-handling, 05-serial-io]

# Tech tracking
tech-stack:
  added: [math (stdlib)]
  patterns:
    - deadline-based sleep using math.ceil(time.time()) eliminates drift accumulation
    - max(0.0, ...) guard prevents ValueError on exact second boundary FP edge case
    - sys.modules registration in _load_module() enables patch('nixichron_gps.time.time')
    - inspect.getsource() structural test for loop ordering (no runtime mocking needed)

key-files:
  created:
    - tests/test_timing.py
  modified:
    - src/nixichron_gps.py

key-decisions:
  - "sys.modules['nixichron_gps'] = mod added to _load_module() so unittest.mock.patch can resolve 'nixichron_gps.time.time' target"
  - "TestLoopOrder uses inspect.getsource(main) string position check — structural guarantee, simpler than runtime call-order mocking"
  - "sleep_until_next_second() placed as Layer 5; parse_args renumbered to Layer 6; main renumbered to Layer 7"

patterns-established:
  - "Deadline sleep: math.ceil(time.time()) computes next tick, sleep the fractional remainder — self-correcting, no drift"
  - "max(0.0, next_tick - now) guard: clamps any FP-negative result to zero (avoids ValueError)"
  - "Module registration: sys.modules['nixichron_gps'] = mod before exec_module so patch targets resolve"
  - "Structural ordering test: inspect.getsource() + string.find() positions instead of runtime mock call-order"

requirements-completed: [TIME-01, TIME-02, TIME-03]

# Metrics
duration: 35min
completed: 2026-04-10
---

# Phase 3 Plan 01: Timing Loop Summary

**math.ceil deadline sleep replaces naive time.sleep(1) in main(), aligning $GPRMC emission to UTC second boundaries with zero drift**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-10T03:54:42Z
- **Completed:** 2026-04-10T04:29:00Z
- **Tasks:** 2 (TDD RED + GREEN)
- **Files modified:** 2

## Accomplishments
- Added `sleep_until_next_second()` as Layer 5: `math.ceil(time.time())` computes next tick, sleeps the fractional remainder, `max(0.0, ...)` guards against FP edge cases
- Reordered `main()` loop: `sleep_until_next_second()` is first, `datetime.now(timezone.utc)` immediately follows — prevents stale timestamps
- Removed `time.sleep(1)` entirely — no naive relative sleep remains
- 6 new tests in `tests/test_timing.py` covering all three TIME requirements; all 30 total tests pass

## Task Commits

1. **Task 1 (RED): Write tests/test_timing.py** - `3b4f2ba` (test)
2. **Task 2 (GREEN): Add sleep_until_next_second() and fix loop order** - `b409f1c` (feat)

**Plan metadata:** (docs commit to follow)

_Note: TDD tasks — test committed first (RED), then implementation (GREEN)_

## Files Created/Modified
- `tests/test_timing.py` - 6 tests across 3 classes: TestSleepUntilNextSecond (4), TestLoopOrder (1), TestTimingIntegration (1)
- `src/nixichron_gps.py` - Added `import math`, `sleep_until_next_second()` at Layer 5, reordered while loop, layer comments renumbered

## Decisions Made

- **sys.modules registration in _load_module():** The plan's patch targets (`nixichron_gps.time.time`) require the module to be findable by name in `sys.modules`. The existing `_load_module()` pattern from `test_cli.py` didn't register it. Added `sys.modules['nixichron_gps'] = mod` before `exec_module`. This was required to avoid `ModuleNotFoundError` in the mock patching.
- **Structural source inspection for loop order test:** `TestLoopOrder.test_timestamp_captured_after_sleep` uses `inspect.getsource(mod.main)` and compares string positions of `sleep_until_next_second()` vs `datetime.now(` — per plan guidance, simpler and more reliable than runtime call-order mocking for this invariant.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added sys.modules registration to _load_module()**
- **Found during:** Task 1 (RED — writing test_timing.py)
- **Issue:** `patch('nixichron_gps.time.time', ...)` raised `ModuleNotFoundError: No module named 'nixichron_gps'` because the module was loaded via `spec_from_file_location` but not registered in `sys.modules` under that name, so `unittest.mock._importer` could not find it.
- **Fix:** Added `sys.modules['nixichron_gps'] = mod` to `_load_module()` before calling `spec.loader.exec_module(mod)`. This is the standard fix for this importlib+mock pattern.
- **Files modified:** `tests/test_timing.py`
- **Verification:** After fix, RED failure changed from `ModuleNotFoundError` to the correct `AttributeError: module 'nixichron_gps' has no attribute 'sleep_until_next_second'` — confirming tests were now running and failing correctly.
- **Committed in:** `3b4f2ba` (Task 1 commit, incorporated into the test file before commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test infrastructure)
**Impact on plan:** Essential fix to make mock patching work. No scope creep. Consistent with the `_load_module()` pattern documentation in the plan's `<interfaces>` section.

## Issues Encountered

None beyond the sys.modules registration deviation documented above.

## Next Phase Readiness

- Phase 04 (signal handling) can build directly on the corrected main() loop
- `sleep_until_next_second()` is in place for Phase 05 (serial I/O) to use unchanged
- All 30 tests green; no regressions in Phases 1-2 test suite

---
*Phase: 03-timing-loop*
*Completed: 2026-04-10*

## Self-Check: PASSED

- FOUND: tests/test_timing.py
- FOUND: src/nixichron_gps.py
- FOUND: .planning/phases/03-timing-loop/03-01-SUMMARY.md
- FOUND commit 3b4f2ba (test RED)
- FOUND commit b409f1c (feat GREEN)
- FOUND commit 40f338d (docs metadata)
