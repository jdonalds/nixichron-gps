---
phase: 05-serial-i-o-and-reconnect
plan: "01"
subsystem: testing
tags: [pyserial, serial, unittest, mock, tdd, backoff, reconnect]

requires:
  - phase: 04-signal-handling
    provides: "_shutdown flag, port = None guard, try/finally in main()"

provides:
  - "tests/test_serial.py with 5 test classes covering SER-01, SER-02, SER-03, SER-04, LOG-02"
  - "Failing RED test scaffold defining the precise contract for open_serial() and write-with-reconnect"

affects:
  - 05-02-PLAN
  - phase-6

tech-stack:
  added: []
  patterns:
    - "patch nixichron_gps.parse_args to return Namespace — avoids sys.argv in unit tests for main()"
    - "mod._shutdown = True in open_serial side_effect — breaks the while-not-_shutdown loop deterministically"
    - "Separate phase_a / phase_b sleep tracking via open_call_count gate — verifies backoff reset on reconnect"

key-files:
  created:
    - tests/test_serial.py
  modified: []

key-decisions:
  - "patch parse_args (return_value=Namespace) rather than patching sys.argv — cleaner isolation of main() under test"
  - "mod._shutdown = True inside fake_open_serial side_effect — reliable loop-break without threading"
  - "9 test methods across 5 classes — exceeds the >=7 minimum in acceptance criteria"

patterns-established:
  - "Pattern: _make_args() helper builds argparse.Namespace — reuse in 05-02 GREEN phase"
  - "Pattern: fake_open_serial sets mod._shutdown=True on success — established loop-break for main() tests"

requirements-completed:
  - SER-01
  - SER-02
  - SER-03
  - SER-04

duration: 5min
completed: 2026-04-10
---

# Phase 05 Plan 01: Serial I/O RED Test Scaffold Summary

**Failing unit test scaffold for serial I/O defining open_serial() constructor contract, port config flow, exponential backoff sequence, reconnect logging, and write-error handling via unittest.mock**

## Performance

- **Duration:** ~5 min
- **Started:** 2026-04-10T04:48:00Z
- **Completed:** 2026-04-10T04:50:34Z
- **Tasks:** 1 (TDD RED)
- **Files modified:** 1

## Accomplishments

- Created `tests/test_serial.py` with 5 test classes and 9 test methods — all failing (RED) against current `nixichron_gps.py`
- Established `_make_args()` helper and `parse_args` mock pattern to test `main()` without touching `sys.argv`
- Defined machine-verifiable contracts for: serial constructor params, port flow, backoff sequence `[1.0, 2.0, 4.0, 8.0, 16.0, 30.0]`, WARNING/INFO logging on reconnect, ERROR logging + port=None on write failure
- Prior test suite (34 tests) remains green

## Task Commits

1. **Task 1: Write tests/test_serial.py — RED (five failing test classes)** - `794e619` (test)

**Plan metadata:** _(docs commit follows)_

## Files Created/Modified

- `tests/test_serial.py` — 5 test classes, 9 tests, all failing against current source (RED confirmed)

## Decisions Made

- Used `patch('nixichron_gps.parse_args', return_value=fake_args)` rather than patching `sys.argv` — cleaner isolation of `main()` logic under test; consistent with how `parse_args(args=None)` was designed for testability
- Used `mod._shutdown = True` inside `fake_open_serial` side_effect to break the `while not _shutdown` loop — avoids threading complexity; deterministic and fast
- 9 test methods (exceeds >=7 minimum) — both backoff scenarios (6-failure sequence, reset-after-reconnect) and both error logging scenarios warrant separate tests for clarity

## Deviations from Plan

None — plan executed exactly as written. The only adjustment was using `patch('nixichron_gps.parse_args', ...)` (cleaner than `sys.argv` patching) which the plan explicitly permitted as a viable loop-breaking approach.

## Issues Encountered

None. The `module does not have attribute 'open_serial'` `AttributeError` on all 9 tests is the expected RED failure — `open_serial` does not yet exist in `nixichron_gps.py`.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `tests/test_serial.py` committed at `794e619` — provides machine-verifiable contract for Plan 05-02 (GREEN implementation)
- Plan 05-02 must: add `import serial`, implement `open_serial()`, replace `else: pass` with write-and-reconnect block
- All 9 tests are expected to pass after Plan 05-02 implementation

## Known Stubs

None — this plan produces test scaffolding only; no production code was written.

---
*Phase: 05-serial-i-o-and-reconnect*
*Completed: 2026-04-10*
