---
phase: 01-core-sentence-engine
plan: 02
subsystem: testing
tags: [python, nmea, gprmc, checksum, self-test, tdd]

# Dependency graph
requires:
  - phase: 01-core-sentence-engine/01-01
    provides: nmea_checksum() and build_gprmc() — the checksum calculator and sentence builder verify_gprmc_checksum and run_self_test validate
provides:
  - verify_gprmc_checksum(): independent XOR checksum verifier (D-02 compliant — no call to nmea_checksum)
  - run_self_test(): 5-sentence self-test runner that prints PASS/FAIL per sentence and exits 0 or 1
  - --self-test CLI entry point in __main__ block
  - tests/test_verify_and_self_test.py: 12 TDD tests covering all verifier and self-test behaviors
affects:
  - Phase 02 (cli-and-dry-run): builds on --self-test entry point and all four functions in nixichron_gps.py
  - Phase 05 (serial-io): will call build_gprmc() that this plan validated correct

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [TDD London School — tests written before implementation, independent-verifier pattern (D-02)]

key-files:
  created: [tests/test_verify_and_self_test.py]
  modified: [src/nixichron_gps.py]

key-decisions:
  - "verify_gprmc_checksum is a fully independent XOR implementation — does not call nmea_checksum() (D-02), catching off-by-one bugs that single-implementation tests would miss"
  - "run_self_test uses fixed base datetime(2026,1,15,12,0,0,utc) with 1-hour increments so all 5 sentences have different time digits"
  - "TDD test fixed build-before-patch ordering: build_gprmc sentence must be constructed before monkey-patching nmea_checksum to test independence"

patterns-established:
  - "Independent verifier pattern: verifier function uses same algorithm as builder but in separate code, enabling true two-implementation testing"
  - "Self-test runner pattern: generates N deterministic sentences from fixed base datetime, exits 0 on all-pass, 1 on any-fail"

requirements-completed: [VAL-01, VAL-02, VAL-03]

# Metrics
duration: 15min
completed: 2026-04-09
---

# Phase 01 Plan 02: Core Sentence Engine — Verifier and Self-Test Summary

**Independent XOR verifier and 5-sentence self-test runner added to nixichron_gps.py, with --self-test CLI entry point exiting 0 on all PASS, proven correct by 12 TDD tests**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-09T00:00:00Z
- **Completed:** 2026-04-09
- **Tasks:** 2 (Task 1: implementation; Task 2: human-verify — auto-approved)
- **Files modified:** 2

## Self-Test Output (copied from terminal)

```
$GPRMC,120000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A*5C  PASS
$GPRMC,130000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A*5D  PASS
$GPRMC,140000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A*5A  PASS
$GPRMC,150000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A*5B  PASS
$GPRMC,160000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A*58  PASS
Exit code: 0
```

## Verification of All 12 Checkpoint Criteria

| # | Criterion | Result |
|---|-----------|--------|
| 1 | Exactly 5 lines ending in "  PASS" (two spaces) | PASS |
| 2 | Each sentence starts with $GPRMC | PASS |
| 3 | Each sentence has exactly 12 commas in the body | PASS |
| 4 | Time fields: 120000.00, 130000.00, 140000.00, 150000.00, 160000.00 | PASS |
| 5 | Status field is A (never V) | PASS |
| 6 | Fields 3-6: 0000.0000,N,00000.0000,E | PASS |
| 7 | Fields 7-8: 0.0,0.0 | PASS |
| 8 | Date field: 150126 (15 Jan 2026, ddmmyy format) | PASS |
| 9 | Fields 10-11 empty (two consecutive commas, nothing between) | PASS |
| 10 | Field 12 (mode indicator) is A | PASS |
| 11 | Checksum after * is two UPPERCASE hex digits | PASS |
| 12 | Exit code is 0 | PASS |

## Line Count

`src/nixichron_gps.py` — 114 lines (under 500 per CLAUDE.md)

## Checkpoint Approval Status

Task 2 checkpoint: **Auto-approved** (--auto mode). All 12 criteria verified programmatically.

## Accomplishments

- verify_gprmc_checksum(): independent XOR verifier — separate from nmea_checksum(), satisfying D-02
- run_self_test(): generates 5 deterministic sentences, prints PASS/FAIL, exits 0 or 1
- --self-test CLI entry point wired in __main__ block
- 12 TDD tests in tests/test_verify_and_self_test.py, all passing GREEN
- Phase 1 complete: all four functions present (nmea_checksum, build_gprmc, verify_gprmc_checksum, run_self_test)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): TDD failing tests** - `5919512` (test)
2. **Task 1 (GREEN): Implementation** - `5485d55` (feat)

_TDD task: RED commit (failing tests) + GREEN commit (implementation passing all tests)_

## Files Created/Modified

- `src/nixichron_gps.py` — added verify_gprmc_checksum(), run_self_test(), __main__ block (56 lines added, 114 total)
- `tests/test_verify_and_self_test.py` — 12 TDD tests for verifier and self-test behaviors (created)

## Decisions Made

- `verify_gprmc_checksum` is a fully independent XOR loop — does not delegate to `nmea_checksum()` (D-02). This catches off-by-one bugs in the builder's checksum delimiter range that single-implementation tests would silently miss.
- Fixed base datetime `datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)` with 1-hour increments was used so all 5 sentences have distinct time digits, exercising multiple digit positions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TDD monkey-patch test ordering**

- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Initial test `test_verify_does_not_call_nmea_checksum` patched `nmea_checksum` before calling `build_gprmc`, causing `build_gprmc` (which legitimately calls `nmea_checksum`) to also trigger the forbidden function — the test failed for the wrong reason.
- **Fix:** Reordered test to build the sentence bytes first, THEN patch `nmea_checksum`, so only `verify_gprmc_checksum` is tested for independence.
- **Files modified:** `tests/test_verify_and_self_test.py`
- **Verification:** All 12 tests pass GREEN after fix.
- **Committed in:** `5485d55` (implementation commit, test fix included)

---

**Total deviations:** 1 auto-fixed (Rule 1 — bug in test logic, not in production code)
**Impact on plan:** Fix was necessary for the D-02 independence test to correctly verify the requirement. No scope creep.

## Issues Encountered

- pytest not installed on system — installed via `pip3 install pytest` (no project dependency added; pytest is a dev tool). No project files changed.

## Known Stubs

None — all functions are fully implemented and wired. No placeholder data, no hardcoded empty values flowing to any output.

## Next Phase Readiness

Phase 1 is complete. All four functions present and verified:
- `nmea_checksum()` — checksum calculator (Plan 01)
- `build_gprmc()` — sentence builder (Plan 01)
- `verify_gprmc_checksum()` — independent verifier (Plan 02)
- `run_self_test()` — self-test runner (Plan 02)
- `--self-test` CLI entry point (Plan 02)

Phase 2 (cli-and-dry-run) can build on top of this complete foundation. The `__main__` block is ready to receive argparse wiring as noted in the code comment.

---
*Phase: 01-core-sentence-engine*
*Completed: 2026-04-09*
