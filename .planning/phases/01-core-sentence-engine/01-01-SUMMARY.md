---
phase: 01-core-sentence-engine
plan: 01
subsystem: nmea
tags: [nmea, gprmc, checksum, python, serial, gps-emulator]

# Dependency graph
requires: []
provides:
  - "nmea_checksum(sentence: str) -> str: XOR checksum over body between '$' and '*', two uppercase hex digits"
  - "build_gprmc(utc_dt) -> bytes: complete $GPRMC sentence as bytes with \\r\\n"
affects:
  - 01-02 (self-test runner depends on these two functions)
  - 02-cli (dry-run mode calls build_gprmc)
  - 03-timing-loop (calls build_gprmc at 1 Hz)
  - 05-serial-io (serial.write() receives build_gprmc output)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure function builder: datetime in, bytes out — no side effects, no clock reads inside"
    - "Two-delimiter checksum: pass '$' + body + '*' so nmea_checksum can always use sentence[1:index('*')]"
    - "NMEA date is ddmmyy (strftime('%d%m%y')), NOT yymmdd — day first"
    - "Use timezone.utc not datetime.UTC for Python 3.9 compatibility"

key-files:
  created:
    - src/nixichron_gps.py
  modified: []

key-decisions:
  - "nmea_checksum receives full '$...body...*' string so the [1:index('*')] slice is always correct"
  - "build_gprmc is a pure function — caller captures datetime.now(timezone.utc) and passes it in (D-05)"
  - "Locked format: $GPRMC,hhmmss.00,A,0000.0000,N,00000.0000,E,0.0,0.0,ddmmyy,,,A*HH\\r\\n (D-11)"
  - "Verified checksum for datetime(2026,4,9,12,34,56,utc): 50 (0x50 = 80 decimal)"

patterns-established:
  - "Pattern 1: Layer 1 checksum before Layer 2 builder — builder calls checksum, not the other way"
  - "Pattern 2: encode('ascii') as the final step — keep all string operations in str, return bytes once"

requirements-completed: [NMEA-01, NMEA-02, NMEA-03, NMEA-04, NMEA-05, NMEA-06, NMEA-07, NMEA-08, NMEA-09]

# Metrics
duration: 2min
completed: 2026-04-10
---

# Phase 01 Plan 01: Core Sentence Engine — nmea_checksum and build_gprmc Summary

**XOR checksum calculator and $GPRMC sentence builder (pure functions, Python 3.9 stdlib only) with verified checksum 50 for 2026-04-09T12:34:56Z**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-10T03:05:41Z
- **Completed:** 2026-04-10T03:06:56Z
- **Tasks:** 2 (1 auto, 1 checkpoint auto-approved)
- **Files modified:** 1

## Accomplishments

- Implemented `nmea_checksum()`: XOR loop over `sentence[1:sentence.index('*')]`, returns `f'{checksum:02X}'` (two uppercase hex digits, zero-padded)
- Implemented `build_gprmc()`: pure function taking UTC `datetime`, returning complete `$GPRMC` sentence as `bytes` with `\r\n` terminator
- VAL-03 satisfied: checksum `50` for `datetime(2026,4,9,12,34,56,tzinfo=timezone.utc)` independently verified by manual XOR computation (80 decimal = 0x50)

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement nmea_checksum() and build_gprmc()** - `5cd83f4` (feat)
2. **Task 2: VAL-03 checkpoint** - auto-approved (no code change, checkpoint only)

**Plan metadata:** (final docs commit — see below)

## Files Created/Modified

- `src/nixichron_gps.py` — contains `nmea_checksum()` and `build_gprmc()` functions (55 lines); no CLI entry point — Phase 2 adds that

## Decisions Made

- Followed all locked decisions from CONTEXT.md (D-01 through D-13) exactly as specified
- `nmea_checksum` receives `'$' + body + '*'` from `build_gprmc` so the `[1:index('*')]` extraction is always safe and consistent whether called from builder or verifier
- File uses Python 3.9-compatible `timezone.utc` throughout (not `datetime.UTC` which requires 3.11+)

## VAL-03 Verification Record

For `datetime(2026, 4, 9, 12, 34, 56, tzinfo=timezone.utc)`:

```
Output: b'$GPRMC,123456.00,A,0000.0000,N,00000.0000,E,0.0,0.0,090426,,,A*50\r\n'
Decoded: $GPRMC,123456.00,A,0000.0000,N,00000.0000,E,0.0,0.0,090426,,,A*50
```

All 5 inspection points confirmed:
1. Starts with `$GPRMC,123456.00,A,` — PASS
2. Ends with `\r\n` — PASS
3. Hex digits `50` are uppercase — PASS
4. Date is `090426` (day=09, month=04, year=26), not `260409` — PASS
5. `repr()` shows `\r\n` at end — PASS

Manual XOR verification: body = `GPRMC,123456.00,A,0000.0000,N,00000.0000,E,0.0,0.0,090426,,,A` → XOR = 80 decimal = 0x50 uppercase = `50`. Matches script output.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Known Stubs

None — the two functions produce real output. No placeholder values. Plan 02 will add `verify_gprmc_checksum()` and `run_self_test()`.

## User Setup Required

None — no external service configuration required. Python 3.9 stdlib only.

## Next Phase Readiness

- `src/nixichron_gps.py` with `nmea_checksum()` and `build_gprmc()` is importable and produces correct output
- Plan 02 can immediately add `verify_gprmc_checksum()` and `run_self_test()` to the same file
- The function signatures established here (pure function, `datetime` in, `bytes` out) must be honored by all downstream phases (2–5)
- No blockers for Plan 02

---
*Phase: 01-core-sentence-engine*
*Completed: 2026-04-10*
