---
phase: 02-cli-shell-and-logging
plan: 01
subsystem: testing
tags: [pytest, tdd, subprocess, argparse, logging]

# Dependency graph
requires:
  - phase: 01-core-sentence-engine
    provides: nixichron_gps.py with build_gprmc, verify_gprmc_checksum, run_self_test
provides:
  - tests/test_cli.py with 12 behavioral contract tests (RED) for Phase 2 CLI and logging
affects:
  - 02-02-PLAN.md (implementation plan that must make all 12 tests GREEN)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "importlib.util.spec_from_file_location to load nixichron_gps.py as a module without triggering __main__"
    - "subprocess.Popen + communicate(timeout=N) + SIGTERM for testing infinite-loop scripts"
    - "Group A/B split: unit tests import module directly; integration tests spawn subprocess"

key-files:
  created:
    - tests/test_cli.py
  modified: []

key-decisions:
  - "test_no_verbose_no_debug passes in RED state — no DEBUG when script exits immediately is correct behavior; test logic is sound and will remain GREEN after implementation"
  - "_load_module() uses importlib.util (not sys.path manipulation) to avoid polluting the module namespace across tests"
  - "subprocess.Popen chosen over subprocess.run for --dry-run tests because the script will run an infinite loop; communicate(timeout=3) then SIGTERM handles clean capture"

patterns-established:
  - "Module loading pattern: importlib.util.spec_from_file_location for non-package single-file scripts"
  - "Subprocess integration pattern: Popen + communicate(timeout) + SIGTERM for long-running processes"
  - "Test grouping: Group A (unit, import-based) vs Group B (integration, subprocess-based)"

requirements-completed:
  - CLI-01
  - CLI-02
  - CLI-03
  - CLI-04
  - LOG-01
  - LOG-03

# Metrics
duration: 1min
completed: 2026-04-10
---

# Phase 02 Plan 01: CLI and Logging Test Scaffold Summary

**12 behavioral-contract tests for argparse CLI and logging coverage of nixichron_gps.py written in TDD RED state using importlib module loading and Popen subprocess integration**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-10T03:32:52Z
- **Completed:** 2026-04-10T03:33:52Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created tests/test_cli.py with 12 tests defining all Phase 2 behavioral contracts
- 7 unit tests (Group A) for parse_args() covering --port, GPS_PORT env var, --dry-run, --self-test, -v/--verbose flags
- 5 integration tests (Group B) for subprocess behavior: $GPRMC output, GPRMC format validation, checksum verification, verbose DEBUG in stderr, no-verbose no-DEBUG
- All 12 Phase 1 tests in test_verify_and_self_test.py remain GREEN (regression guard confirmed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write test_cli.py — all 12 tests in RED state** - `bc5f377` (test)

**Plan metadata:** _(docs commit to follow)_

## Files Created/Modified
- `tests/test_cli.py` - 12 behavioral contract tests for Phase 2 CLI/logging (RED state, 11 failing, 1 passing)

## Decisions Made
- `test_no_verbose_no_debug` passes in RED state because the script exits immediately without producing any output (no DEBUG in empty stderr). This is correct behavior — the test logic is sound and will remain GREEN after Plan 02 implementation.
- Used `importlib.util.spec_from_file_location` (not sys.path insertion) to load the module without triggering `__main__`, matching the pattern established in Phase 1 research.
- `subprocess.Popen` with `communicate(timeout=3)` + `SIGTERM` is the canonical approach for testing scripts that will run as infinite loops.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None - all acceptance criteria met on first attempt.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- tests/test_cli.py is complete and defines exact behavioral contracts Plan 02 must satisfy
- Plan 02 (Wave 2) adds parse_args(), setup_logging(), and main() to nixichron_gps.py
- All 12 tests will turn GREEN when Plan 02 implementation is complete
- Phase 1 regression guard confirmed: test_verify_and_self_test.py continues passing

---
*Phase: 02-cli-shell-and-logging*
*Completed: 2026-04-10*
