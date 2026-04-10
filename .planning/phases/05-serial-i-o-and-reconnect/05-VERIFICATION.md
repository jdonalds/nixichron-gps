---
phase: 05-serial-i-o-and-reconnect
verified: 2026-04-09T22:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
human_verification:
  - test: "Physical hardware end-to-end: NixiChron clock displays UTC time"
    expected: "Clock advances at 1 Hz, shows correct UTC hour/minute/second"
    why_human: "Requires physical USB-serial adapter and NixiChron clock hardware"
  - test: "Physical USB unplug/replug reconnect"
    expected: "Script retries with exponential backoff, logs WARNING on disconnect, logs INFO on reconnect, resumes sending sentences within 30s"
    why_human: "Cannot simulate real hardware disconnect in automated tests"
---

# Phase 5: Serial I/O and Reconnect — Verification Report

**Phase Goal:** The script opens the serial port at 4800 baud/8N1 and sends sentences to the NixiChron clock, recovering automatically from disconnects without crashing
**Verified:** 2026-04-09T22:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `open_serial()` helper exists and calls `serial.Serial` with exact 4800/8N1/no-flow parameters | VERIFIED | Lines 167-184 of `src/nixichron_gps.py`; `baudrate=4800`, `bytesize=serial.EIGHTBITS`, `parity=serial.PARITY_NONE`, `stopbits=serial.STOPBITS_ONE`, `xonxoff=False`, `rtscts=False`, `dsrdtr=False`, `write_timeout=2` all present |
| 2 | The `else: pass` placeholder is replaced with a full write-and-reconnect block | VERIFIED | Lines 259-283; inner open-loop, write, and write-failure handler all implemented; no bare `pass` remaining |
| 3 | Write failure sets `port = None` (triggers reconnect) and logs at ERROR level | VERIFIED | Line 275: `logger.error('Write error on %s: %s', ...)`, line 283: `port = None  # triggers re-open`; `TestErrorLogging` (2 tests) pass |
| 4 | Inner reconnect loop guards on `and not _shutdown` so SIGTERM does not hang | VERIFIED | Line 261: `while port is None and not _shutdown:` |
| 5 | All five test classes in `tests/test_serial.py` pass GREEN | VERIFIED | `python3 -m pytest tests/test_serial.py -q` → `9 passed in 0.02s` |
| 6 | Full test suite (all prior phases) remains green | VERIFIED | `python3 -m pytest tests/ -q` → `43 passed in 36.34s` |

**Score:** 6/6 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tests/test_serial.py` | 5 test classes (SER-01, SER-02, SER-03, SER-04, LOG-02) | VERIFIED | 395 lines; 5 classes (`TestOpenSerial`, `TestPortConfig`, `TestBackoff`, `TestReconnectLogging`, `TestErrorLogging`); 9 test methods |
| `src/nixichron_gps.py` | `open_serial()` helper function | VERIFIED | Lines 167-184; full implementation with all required params |
| `src/nixichron_gps.py` | `import serial` at module level | VERIFIED | Line 16 |
| `src/nixichron_gps.py` | Write-with-reconnect block in `main()` else branch | VERIFIED | Lines 258-283; replaces former `else: pass` |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `main()` else branch | `open_serial()` | `if port is None: port = open_serial(args.port)` | VERIFIED | Line 263: `port = open_serial(args.port)` |
| `open_serial()` | `serial.Serial()` | `return serial.Serial(port=port, baudrate=4800, ...)` | VERIFIED | Lines 174-184; all 8 keyword args present |
| Write failure handler | `port = None` | Sets sentinel after `SerialException` on `port.write()` | VERIFIED | Line 283: `port = None  # triggers re-open on next iteration` |
| `tests/test_serial.py` | `src/nixichron_gps.py` | `importlib.util.spec_from_file_location` | VERIFIED | Lines 35-38; consistent with established pattern |

---

### Data-Flow Trace (Level 4)

Not applicable — this phase delivers serial I/O (daemon output), not UI components rendering dynamic data. The data flow is: `build_gprmc(utc_dt)` → `port.write(sentence)` → serial hardware. This is verified functionally by `--self-test` (5 PASS sentences) and the test suite.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `--self-test` still exits 0 and prints PASS | `python3 src/nixichron_gps.py --self-test` | 5 × PASS, exit 0 | PASS |
| All 9 serial tests pass | `python3 -m pytest tests/test_serial.py -q` | `9 passed in 0.02s` | PASS |
| Full 43-test suite passes | `python3 -m pytest tests/ -q` | `43 passed in 36.34s` | PASS |
| AST parses without error | `python3 -c "import ast, pathlib; ast.parse(pathlib.Path('src/nixichron_gps.py').read_text()); print('AST OK')"` | `AST OK` | PASS |
| File under 500 lines | `wc -l src/nixichron_gps.py` | 291 lines | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SER-01 | 05-01-PLAN.md, 05-02-PLAN.md | Serial port at 4800 baud, 8N1, no flow control | SATISFIED | `open_serial()` lines 167-184; `TestOpenSerial` passes |
| SER-02 | 05-01-PLAN.md, 05-02-PLAN.md | Port configurable via `--port`, `GPS_PORT`, or default | SATISFIED | `args.port` passed to `open_serial(args.port)` (line 263); `TestPortConfig` passes |
| SER-03 | 05-01-PLAN.md, 05-02-PLAN.md | Exponential backoff: 1s, 2s, 4s… capped at 30s | SATISFIED | Lines 245-270; `_delay = min(_delay * 2, _BACKOFF_MAX)`; `TestBackoff` passes with sequence `[1.0, 2.0, 4.0, 8.0, 16.0, 30.0]` |
| SER-04 | 05-01-PLAN.md, 05-02-PLAN.md | Reconnect logged at WARNING; success at INFO | SATISFIED | Line 264: `logger.info`; line 268: `logger.warning`; `TestReconnectLogging` passes |
| LOG-02 | 05-01-PLAN.md (deferred from Phase 2) | Serial errors logged at ERROR level | SATISFIED | Line 267: `logger.error('Cannot open ...')`, line 275: `logger.error('Write error ...')`; `TestErrorLogging` passes |

**Orphaned requirements note:** REQUIREMENTS.md still shows LOG-02 as `[ ]` (unchecked) and the traceability table shows `LOG-02 | Phase 2 | Pending`. The implementation is complete and tested, but REQUIREMENTS.md was not updated when Phase 5 delivered LOG-02. This is a documentation gap only — no implementation is missing.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/nixichron_gps.py` | 279-283 | `port.close()` called before `port = None` | Info | SUMMARY.md claims the opposite ordering ("port = None set after delay sleep, before port.close()"). The actual code closes then nulls. The tests still pass because they verify reconnect behavior, not operation order. If `close()` raises an exception, the `except Exception: pass` guard prevents the `port = None` from executing — however this is inside an `except serial.SerialException` outer block, so `close()` raising is extremely unlikely in practice. Not a blocker. |

No TODOs, FIXMEs, placeholders, empty returns, or bare `pass` statements found in the modified files.

---

### Human Verification Required

#### 1. NixiChron Clock End-to-End Display

**Test:** Connect a USB-to-serial adapter, run `python3 src/nixichron_gps.py --port /dev/tty.usbserial-X` (or the correct device path), observe the NixiChron clock
**Expected:** Clock displays current UTC time advancing at 1 Hz
**Why human:** Requires physical hardware (USB-serial adapter, DB9 cable, NixiChron clock) that cannot be simulated

#### 2. USB Unplug Reconnect Recovery

**Test:** With the script running (without `--dry-run`), unplug the USB-serial adapter, observe log output, then replug
**Expected:** Script logs `logger.error` on write failure, then `logger.warning` during retry, then `logger.info` on reconnect; clock resumes displaying UTC time within 30s; script does not crash
**Why human:** Physical hardware disconnect cannot be simulated in automated tests without a real serial device

---

### Gaps Summary

No implementation gaps. All six derived truths are verified, all required artifacts exist and are substantive and wired, all four PLAN-declared key links are present in the code, all five requirements (SER-01 through SER-04, LOG-02) have concrete implementation evidence and passing tests.

Two informational items noted:

1. **REQUIREMENTS.md documentation gap**: LOG-02 checkbox and traceability row were not updated to reflect Phase 5 completion. The implementation is fully present and tested. This does not block Phase 6.

2. **Minor SUMMARY vs. code discrepancy**: The `port.close()` / `port = None` ordering in the write-failure handler is reversed from what SUMMARY.md documents. The `except Exception: pass` guard around `close()` means this is safe in practice, and all tests pass. Not a blocker.

---

_Verified: 2026-04-09T22:00:00Z_
_Verifier: Claude (gsd-verifier)_
