# Architecture Patterns

**Domain:** Single-script GPS NMEA emulator (Python)
**Project:** NixiChron GPS Emulator (`nixichron_gps.py`)
**Researched:** 2026-04-09

## Recommended Architecture

A single flat file with clearly separated functional sections. No classes are required; plain functions grouped by concern, called from a `main()` entry point. This keeps the script approachable and directly deployable.

```
nixichron_gps.py
├── [1] Imports and constants
├── [2] Checksum calculator
├── [3] NMEA sentence builder
├── [4] Serial port abstraction (open / write / close)
├── [5] Retry / backoff logic
├── [6] Top-of-second sleep helper
├── [7] Signal handler + shutdown flag
├── [8] Self-test runner
├── [9] CLI argument parser + logging setup
└── [10] main() — main loop
```

## Component Boundaries

| Component | Responsibility | Inputs | Outputs | Communicates With |
|-----------|---------------|--------|---------|-------------------|
| **Checksum calculator** | XOR all bytes between `$` and `*`; return two uppercase hex chars | Raw sentence body string | `str` (2 hex chars) | NMEA builder |
| **NMEA sentence builder** | Assemble `$GPRMC` fields; attach checksum; terminate with `\r\n` | `datetime` (UTC) | `bytes` (encoded sentence) | Checksum calculator, main loop |
| **Serial port abstraction** | Open port with 4800/8N1; write bytes; close on shutdown; raise `serial.SerialException` | Port path `str`, bytes to send | None / raises | Main loop, retry logic |
| **Retry / backoff** | Catch `SerialException`; sleep with exponential delay (cap 30 s); retry open | Exception, current delay | Updated delay `float` | Serial abstraction |
| **Top-of-second sleep** | Calculate fractional seconds remaining until next whole UTC second; call `time.sleep()` | Current `datetime.now(timezone.utc)` | None (blocks until boundary) | Main loop |
| **Signal handler** | Set a module-level `_shutdown` flag on SIGTERM/SIGINT; nothing else | OS signal | `_shutdown = True` | Main loop (polls flag) |
| **Self-test runner** | Generate 5 sentences, verify each checksum, print pass/fail, `sys.exit(0/1)` | None | stdout + exit code | Checksum calculator, NMEA builder |
| **CLI / logging setup** | Parse `--port`, `--dry-run`, `--self-test`; configure `logging` | `sys.argv` | `argparse.Namespace` | `main()` |
| **Main loop** | Poll `_shutdown`; sleep to boundary; build sentence; write or print; handle errors | All of the above | Bytes to port or stdout | All components |

## Data Flow

```
sys.argv
    │
    ▼
[CLI parser + logging setup]
    │
    ├─── --self-test ──► [Self-test runner] ──► stdout ──► sys.exit
    │
    ▼
main()
    │
    ├── loop entry: check _shutdown flag (set by signal handler)
    │
    ├── [Top-of-second sleep] ◄── datetime.now(timezone.utc)
    │        blocks until next second boundary
    │
    ├── datetime.now(timezone.utc)   ← timestamp for sentence
    │        │
    │        ▼
    │   [NMEA builder]
    │        │
    │        ├── formats fields (hhmmss.ss, ddmmyy, dummy lat/lon/speed/track)
    │        ├── calls [Checksum calculator]
    │        └── returns bytes: b"$GPRMC,...*XX\r\n"
    │
    ├── --dry-run?
    │     YES ──► sys.stdout.write(decoded sentence)
    │     NO  ──► [Serial port abstraction].write(bytes)
    │                   │
    │                   └── SerialException?
    │                           │
    │                           ▼
    │                   [Retry / backoff]
    │                     sleep(delay); delay = min(delay*2, 30)
    │                     loop back to re-open port
    │
    └── SIGTERM/SIGINT ──► [Signal handler] ──► _shutdown = True
                                                     │
                                              main loop exits cleanly
                                              [Serial port abstraction].close()
```

## NMEA Sentence Structure (GPRMC)

```
$GPRMC,HHMMSS.SS,A,LLLL.LL,N,YYYYY.YY,E,0.0,0.0,DDMMYY,,A*XX\r\n
│      │          │  │       │  │         │  │   │   │      │  │  │
│      UTC time   │  Lat     │  Lon       │  │   │  Date    │  │  XOR checksum
│                 │          │            │  │   Track     empty  Mode=Autonomous
│                 Status=A   Lat dir      │  Speed=0         Mag var omitted
│                                         Lon dir
Sentence ID
```

Field mapping for emulator (dummy position: 0000.00,N,00000.00,E):
- Field 1 (UTC): `datetime.strftime("%H%M%S.00")` — always `.00` (whole seconds)
- Field 2 (Status): `A` (always valid)
- Fields 3-6 (Lat/Lon): dummy zeros
- Field 7 (Speed): `0.0`
- Field 8 (Track): `0.0`
- Field 9 (Date): `datetime.strftime("%d%m%y")`
- Field 10 (Mag var): empty
- Field 11 (Mode): `A` (Autonomous)

Source: NovAtel OEM7 GPRMC documentation confirms Mode indicator `A` = Autonomous. [HIGH confidence]

## Top-of-Second Timing Pattern

```python
import time
from datetime import datetime, timezone

def sleep_to_next_second():
    now = datetime.now(timezone.utc)
    fraction = now.microsecond / 1_000_000
    time.sleep(1.0 - fraction)
```

This uses `datetime.now(timezone.utc)` (the project-mandated clock source) to calculate the fractional part of the current second and sleeps the complement. The resulting wakeup lands at approximately the top of the next second. There is no perfect sub-millisecond precision guarantee from userspace Python, but for a 1 Hz NMEA feed to a Nixie clock this is more than adequate.

`time.sleep()` internally uses the monotonic clock so the sleep duration is not affected by NTP corrections mid-sleep. [HIGH confidence — Python docs]

## Signal Handling Pattern

```python
import signal

_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True

signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)
```

The handler only sets the flag. No I/O, no logging. The main loop checks `_shutdown` at the top of each iteration. Port closure happens in a `finally` block in `main()`, not in the handler. This avoids GIL-related issues with blocking I/O inside signal handlers. [HIGH confidence — Python signal docs]

## Retry / Backoff Pattern

```python
import time
import serial

BACKOFF_INITIAL = 1.0   # seconds
BACKOFF_MAX = 30.0      # seconds

delay = BACKOFF_INITIAL
while not _shutdown:
    try:
        port = serial.Serial(port_path, baudrate=4800, bytesize=8,
                             parity='N', stopbits=1, timeout=1)
        delay = BACKOFF_INITIAL  # reset on successful open
        # inner send loop ...
    except serial.SerialException as exc:
        logging.error("Serial error: %s — retry in %.0fs", exc, delay)
        time.sleep(delay)
        delay = min(delay * 2, BACKOFF_MAX)
```

No external retry library is needed. Pure standard-library implementation is simpler and has no dependency. Third-party libraries (`tenacity`, `backoff`) add nothing for a single exception type with a trivial backoff formula. [MEDIUM confidence — standard pattern]

## Dry-Run Abstraction

Dry-run mode does not require a separate class. A single boolean flag from the parsed args determines whether bytes go to `serial.Serial.write()` or `sys.stdout.buffer.write()`. The NMEA builder always returns `bytes`; the dispatch point is in `main()`.

```python
if args.dry_run:
    sys.stdout.buffer.write(sentence_bytes)
    sys.stdout.buffer.flush()
else:
    port.write(sentence_bytes)
```

Using `sys.stdout.buffer` (the raw binary buffer) keeps the abstraction clean — the same `bytes` object is used in both paths.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Sleeping a flat 1.0 second
**What goes wrong:** Drift accumulates. Each iteration takes slightly more than 1 second due to sentence build + write time. Over minutes the emitter drifts measurably behind the clock.
**Instead:** Always compute the sleep duration from the current fractional second, not from a fixed interval.

### Anti-Pattern 2: Logging or I/O inside signal handler
**What goes wrong:** Can deadlock under CPython's GIL if the signal fires while the main thread is inside a `write()` call.
**Instead:** Set only a boolean flag; do all cleanup in `finally`.

### Anti-Pattern 3: Computing UTC time before the sleep
**What goes wrong:** The timestamp captured before the sleep is stale by up to one second when the sentence is actually sent.
**Instead:** Capture `datetime.now(timezone.utc)` after waking from the sleep, immediately before building the sentence.

### Anti-Pattern 4: Encoding the sentence as a string to stdout in dry-run but bytes to serial
**What goes wrong:** Two code paths diverge; checksum validation in self-test only tests one path.
**Instead:** NMEA builder always returns `bytes`. Both paths accept `bytes`.

## Suggested Build Order

Dependencies determine order. Each layer can only be tested after the layer it depends on exists.

```
Layer 1 — Checksum calculator
  No dependencies. Pure function. Testable immediately.
  Required by: NMEA builder, self-test runner.

Layer 2 — NMEA sentence builder
  Depends on: checksum calculator.
  Testable with frozen datetime; produces known expected output.
  Required by: main loop, self-test runner.

Layer 3 — Self-test runner
  Depends on: NMEA builder, checksum calculator.
  No serial port needed. Exit-code test validates the core logic chain.
  Required by: --self-test CLI flag.

Layer 4 — CLI parser + logging setup
  No domain dependencies.
  Controls which code path runs (dry-run, self-test, real).
  Required by: main().

Layer 5 — Top-of-second sleep helper
  Depends on: datetime, time. No domain dependencies.
  Required by: main loop.

Layer 6 — Signal handler + shutdown flag
  No domain dependencies.
  Required by: main loop (polls _shutdown).

Layer 7 — Serial port abstraction + retry/backoff
  Depends on: pyserial, shutdown flag.
  Testable with --dry-run before hardware is available.
  Required by: main loop (real mode).

Layer 8 — Main loop (main())
  Depends on: all of the above.
  Integration point. Wire everything together.
  Testable end-to-end with --dry-run and --self-test.
```

Recommended implementation sequence:
1. Checksum calculator + unit test
2. NMEA sentence builder + unit test with fixed datetime
3. Self-test runner (proves layers 1-2 correct before any I/O)
4. CLI parser + logging
5. Timing helper
6. Signal handler
7. Main loop with dry-run first (no hardware needed)
8. Serial port open/write/close + backoff (real hardware or loopback device)

## Scalability Considerations

This script is intentionally a singleton. No scalability concerns apply.

| Concern | Relevance |
|---------|-----------|
| Multiple clocks | Out of scope by project decision |
| Multiple sentence types | Out of scope; NixiChron needs only GPRMC |
| Threading | Not needed; single serial TX, no RX |
| Async | Not needed; 1 Hz loop is trivially simple |

## Sources

- [NovAtel OEM7 GPRMC documentation](https://docs.novatel.com/OEM7/Content/Logs/GPRMC.htm) — field list, Mode indicator values [HIGH confidence]
- [Python signal module docs](https://docs.python.org/3/library/signal.html) — signal handler constraints [HIGH confidence]
- [Python time module docs](https://docs.python.org/3/library/time.html) — monotonic clock, sleep behavior [HIGH confidence]
- [pySerial 3.5 API docs](https://pyserial.readthedocs.io/en/latest/pyserial_api.html) — Serial class, SerialException [HIGH confidence]
- [NMEA checksum recipe](https://code.activestate.com/recipes/576789-nmea-sentence-checksum/) — XOR pattern [MEDIUM confidence]
- [Graceful SIGTERM in Python](https://dnmtechs.com/graceful-sigterm-signal-handling-in-python-3-best-practices-and-implementation/) — sentinel flag pattern [MEDIUM confidence]
