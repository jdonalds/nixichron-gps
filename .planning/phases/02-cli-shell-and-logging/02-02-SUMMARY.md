---
phase: 02-cli-shell-and-logging
plan: 02
subsystem: cli
tags: [argparse, logging, nmea, gprmc, dry-run, self-test]

# Dependency graph
requires:
  - phase: 02-cli-shell-and-logging
    provides: "RED test scaffold: 12 Phase 2 tests in tests/test_cli.py"
  - phase: 01-core-sentence-engine
    provides: "nmea_checksum, build_gprmc, verify_gprmc_checksum, run_self_test"
provides:
  - "parse_args(args=None) -> argparse.Namespace with --port, --dry-run, --self-test, --verbose/-v"
  - "setup_logging(verbose: bool) using logging.basicConfig on stderr"
  - "main() dispatch: self_test branch + dry-run loop writing to sys.stdout.buffer"
  - "Proper if __name__ == '__main__': main() entry point"
affects: [03-timing-loop, 05-serial-io]

# Tech tracking
tech-stack:
  added: [argparse, logging, os, time]
  patterns:
    - "Module-level logger = logging.getLogger('nixichron') — no calls at import time"
    - "parse_args(args=None) pattern for unit-testable argparse without sys.argv pollution"
    - "sys.stdout.buffer.write for binary NMEA bytes (preserves \\r\\n)"
    - "setup_logging called from main() after parse_args() — basicConfig one-shot"

key-files:
  created: []
  modified:
    - src/nixichron_gps.py

key-decisions:
  - "parse_args takes args=None so unit tests can pass ['--port', '/dev/foo'] without touching sys.argv"
  - "setup_logging called from main() not at module level — logging.basicConfig is one-shot, must know verbose flag first"
  - "sys.stdout.buffer.write (not sys.stdout.write) — preserves exact CRLF bytes required by NixiChron"
  - "run_self_test() keeps print() calls; logger goes to stderr — self-test output must be on stdout"

patterns-established:
  - "Layer numbering (4/5/6) continues Phase 1 convention (1/2/3a/3b)"
  - "Each Layer separated by comment block with requirement IDs (LOG-xx, CLI-xx)"

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04, LOG-01, LOG-03]

# Metrics
duration: 8min
completed: 2026-04-10
---

# Phase 02 Plan 02: CLI Shell and Logging Summary

**argparse CLI shell with parse_args/setup_logging/main() turning all 12 RED Phase 2 tests GREEN while keeping all 12 Phase 1 tests GREEN**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-10T03:35:48Z
- **Completed:** 2026-04-10T03:43:00Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Expanded imports (argparse, logging, os, time) and added module-level `logger = logging.getLogger('nixichron')`
- Implemented `parse_args(args=None)` with --port, --dry-run, --self-test, --verbose/-v flags; GPS_PORT env fallback
- Implemented `setup_logging(verbose)` called from main() after parse_args — not at module level
- Implemented `main()` dispatch: self_test branch + infinite loop writing to `sys.stdout.buffer` in dry-run mode
- Replaced bare `sys.argv` entry point with `if __name__ == '__main__': main()`
- All 24 tests pass (12 Phase 1 + 12 Phase 2); file is exactly 200 lines

## Task Commits

Each task was committed atomically:

1. **Task 1: Add imports and module-level logger** - `195bdce` (feat)
2. **Task 2: Add parse_args(), setup_logging(), main() and replace entry point** - `00a1b10` (feat)

**Plan metadata:** (docs commit below)

## Files Created/Modified

- `src/nixichron_gps.py` - Added Layers 4/5/6: setup_logging, parse_args, main; replaced Phase 1 entry point

## Decisions Made

- `parse_args(args=None)` pattern chosen so unit tests inject arg lists without touching sys.argv
- `setup_logging` called from `main()` not at module import time — `logging.basicConfig` is one-shot; calling at module level would bake INFO level before `--verbose` is parsed
- `sys.stdout.buffer.write` (binary) not `sys.stdout.write` (text) — preserves the exact `\r\n` bytes the NixiChron clock firmware requires
- `run_self_test()` keeps `print()` for its output — self-test output is on stdout; logger writes to stderr by default

## Deviations from Plan

None - plan executed exactly as written. The only adjustments were minor docstring trimming to bring the file from 204 to 200 lines to satisfy the "between 170 and 200 lines" acceptance criterion.

## Issues Encountered

None. All tests passed on first run after implementation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 (timing loop): `time.sleep(1)` in `main()` is the Phase 3 placeholder; replace with `time.sleep(math.ceil(time.time()) - time.time())` for top-of-second alignment
- Phase 5 (serial I/O): The `else: pass` branch in `main()` is the Phase 5 insertion point for `serial.Serial.write(sentence)`
- Both integration points are clearly commented in src/nixichron_gps.py

---
*Phase: 02-cli-shell-and-logging*
*Completed: 2026-04-10*
