---
phase: 04-signal-handling
plan: 01
subsystem: testing
tags: [pytest, signal, SIGTERM, SIGINT, subprocess, tdd, red-phase]

# Dependency graph
requires:
  - phase: 03-timing-loop
    provides: main() loop with sleep_until_next_second() and --dry-run subprocess test pattern
provides:
  - tests/test_signal.py with 4 failing RED tests locking SIG-01 and SIG-02 acceptance criteria
affects: [04-02-signal-handling-implementation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "subprocess stdout.read(64) loop with deadline to detect loop start before sending signal"
    - "SRC_PATH.read_text() for source inspection tests (no _load_module() needed)"

key-files:
  created:
    - tests/test_signal.py
  modified: []

key-decisions:
  - "Used proc.stdout.read(64) loop with 5s deadline to detect loop start — avoids fixed time.sleep() which is flaky"
  - "Source inspection via SRC_PATH.read_text() not _load_module() — avoids executing module for structural checks"
  - "test_sigterm returncode -15 confirms SIGTERM kills without handler (RED correctly fails)"
  - "test_sigint returncode -2 + traceback confirms SIGINT raises KeyboardInterrupt (RED correctly fails)"

patterns-established:
  - "Signal test pattern: Popen + stdout read loop for start detection + send_signal + communicate(timeout=5)"
  - "Source inspection pattern: SRC_PATH.read_text() + string/regex search for structural assertions"

requirements-completed: [SIG-01, SIG-02]

# Metrics
duration: 3min
completed: 2026-04-10
---

# Phase 4 Plan 01: Signal Handling RED Tests Summary

**Four failing pytest tests locking SIGTERM/SIGINT clean-exit and _shutdown-flag/try-finally structural requirements before any implementation**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-10T04:23:33Z
- **Completed:** 2026-04-10T04:26:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments

- Created tests/test_signal.py with TestSignalHandling (subprocess integration) and TestShutdownFlag (source inspection) classes
- Confirmed all 4 tests fail RED against current source: SIGTERM exits -15, SIGINT exits -2 with traceback, no `_shutdown` flag, no `try/finally`
- Verified existing 30 tests (test_cli.py, test_timing.py, test_verify_and_self_test.py) still pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Write tests/test_signal.py (RED)** - `6147e47` (test)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/test_signal.py` - Four TDD RED tests: test_sigterm_clean_exit, test_sigint_clean_exit, test_loop_uses_shutdown_flag, test_finally_block_present

## Decisions Made

- Used `proc.stdout.read(64)` polling loop with 5-second deadline to detect when the main loop has started, rather than `time.sleep()` — more reliable on slower machines
- Source inspection uses `SRC_PATH.read_text()` directly (no `_load_module()`) since we need raw text search, not module execution
- Kept test structure consistent with test_timing.py conventions (PROJECT_ROOT/SRC_PATH pattern, same imports)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- RED phase complete: acceptance criteria locked in tests/test_signal.py
- Ready for Phase 04 Plan 02: implement _shutdown flag, signal handlers, and try/finally in src/nixichron_gps.py to turn all 4 tests GREEN

---
*Phase: 04-signal-handling*
*Completed: 2026-04-10*
