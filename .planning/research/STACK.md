# Technology Stack

**Project:** NixiChron GPS Emulator (`nixichron_gps.py`)
**Researched:** 2026-04-09
**Domain:** Python CLI tool — serial port NMEA emitter

---

## Recommended Stack

### Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.9+ | Runtime | Project constraint. All stdlib modules below are available in 3.9. No third-party runtime required beyond pyserial. |

Python 3.9 is the floor. Do not use syntax or stdlib additions from 3.10+ (no `match/case`, no `X | Y` union types in annotations, no `datetime.UTC` alias — that arrived in 3.11). The project is a single script with one external dependency.

### Serial Communication

| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pyserial | 3.5 | Serial port I/O | The only maintained, cross-platform Python serial library. Production/Stable status. Handles RS-232 over USB adapters on macOS and Linux. Version 3.5 is the latest stable release (November 2020); the project has not released a 3.6. No viable alternative exists. |

**Configuration for NixiChron (4800 baud, 8N1, no flow control):**

```python
import serial

port = serial.Serial(
    port="/dev/cu.usbserial-XXXX",  # macOS: use /dev/cu.* not /dev/tty.*
    baudrate=4800,
    bytesize=serial.EIGHTBITS,      # 8
    parity=serial.PARITY_NONE,      # N
    stopbits=serial.STOPBITS_ONE,   # 1
    xonxoff=False,                  # no software flow control
    rtscts=False,                   # no RTS/CTS hardware flow control
    dsrdtr=False,                   # no DSR/DTR hardware flow control
    write_timeout=2,                # surface stall quickly; None blocks forever
)
```

**macOS device name:** Always use `/dev/cu.usbserial-*` not `/dev/tty.usbserial-*`. The `cu.*` (calling unit) variant does not block on DCD assertion, which is correct for a one-way transmit-only connection. The `tty.*` variant blocks `open()` until DCD is asserted by the remote device — the NixiChron does not assert DCD.

**Confidence: HIGH** — verified against pyserial official docs and macOS serial device behaviour documentation.

### Datetime / UTC Handling

Use only Python stdlib `datetime` module. No external library.

```python
from datetime import datetime, timezone

now = datetime.now(timezone.utc)   # Python 3.9-compatible, timezone-aware
```

**Do not use:**
- `datetime.utcnow()` — deprecated in Python 3.12, returns a naive datetime (no tzinfo), incorrect for explicit UTC work.
- `datetime.UTC` — alias for `timezone.utc` added in Python 3.11; breaks on Python 3.9 and 3.10.
- `ntplib` or any NTP client — the project constraint excludes this; the host OS clock is already NTP-disciplined.
- `pytz` — obsolete; replaced by stdlib `zoneinfo` in 3.9. Not needed here because the output is always UTC.
- `zoneinfo` — not needed; this application only ever uses UTC.

**Confidence: HIGH** — confirmed against Python 3 official docs and migration article from Miguel Grinberg.

### Timing — Top-of-Second Alignment

Use stdlib `time` module only. The correct pattern to align sends to the top of each second is:

```python
import time

while running:
    now = time.time()
    sleep_duration = 1.0 - (now % 1.0)
    time.sleep(sleep_duration)
    # send sentence immediately after waking
```

`time.sleep()` accepts floats. OS scheduling jitter is typically <10ms on modern macOS/Linux, which is negligible for a 1-second NMEA sentence interval. The NixiChron clock latches on the second field in the sentence, not on the exact arrival time of the serial byte, so sub-10ms jitter does not affect display accuracy.

**Do not use:**
- `time.monotonic()` alone — monotonic clock is useful for measuring elapsed time but does not give you wall-clock seconds. The `%` modulo trick requires `time.time()` (wall clock) to align to real UTC seconds.
- `asyncio` event loop — adds complexity with no benefit for a single-loop, single-port script.
- `py-abs-sleep` or other third-party timing libraries — unnecessary for this use case.

**Confidence: MEDIUM** — pattern is established practice; jitter tolerance confirmed by understanding of NMEA clock consumer behaviour.

### Signal Handling

Use stdlib `signal` module. Flag-based pattern is the correct approach for a simple main loop.

```python
import signal

_running = True

def _shutdown(signum, frame):
    global _running
    _running = False

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)
```

The main loop checks `_running` on each iteration and performs port cleanup before exit. Signal handlers must be registered in the main thread (Python constraint). Do not perform blocking I/O or raise exceptions inside the handler — the handler only sets the flag.

**Do not use:**
- `KeyboardInterrupt` as the sole shutdown mechanism — SIGTERM (systemd stop, `kill`) will not trigger it.
- `atexit` module as the only mechanism — `atexit` runs on normal exit but may not run on SIGTERM without the flag pattern.
- Socket-pair pattern (from Python signal docs) — correct for event-loop programs, overkill for a simple while loop.

**Confidence: HIGH** — pattern confirmed against Python official signal documentation.

### Logging

Use stdlib `logging` module. No third-party logging library.

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

logger.debug("Sent: %s", sentence)     # every sentence
logger.error("Serial error: %s", e)   # failures
```

**Configuration at runtime:** Use `--verbose` / `-v` to set `logging.DEBUG`; default to `logging.INFO` so normal operation is quiet. Error logs always appear regardless of verbosity level.

**Do not use:**
- `structlog` — excellent library for services, but adds a dependency and JSON output is unnecessary for a single-user CLI tool.
- `print()` — use only for `--dry-run` sentence output (which is intentional stdout, not logging).
- Root logger `logging.warning(...)` calls — always use a named logger via `getLogger(__name__)`.

**Confidence: HIGH** — stdlib logging is the correct choice for a single-script CLI tool with zero infrastructure.

### CLI Argument Parsing

Use stdlib `argparse`. No third-party library.

```python
import argparse

parser = argparse.ArgumentParser(
    description="NMEA GPS time emulator for NixiChron Nixie clock"
)
parser.add_argument("--port", default="/dev/ttyUSB0",
                    help="Serial port (default: /dev/ttyUSB0, env: NIXICHRON_PORT)")
parser.add_argument("--dry-run", action="store_true",
                    help="Print sentences to stdout instead of serial port")
parser.add_argument("--self-test", action="store_true",
                    help="Generate 5 sentences, validate checksums, exit")
parser.add_argument("-v", "--verbose", action="store_true",
                    help="Enable DEBUG logging")
```

Environment variable fallback for `--port` using `os.environ.get("NIXICHRON_PORT", "/dev/ttyUSB0")` as the `default=` value.

**Do not use:**
- `click` — decorator-based, cleaner DX, but adds a dependency. `argparse` is stdlib and sufficient.
- `typer` — requires Python 3.6+ and type annotations; adds a dependency for no benefit here.

**Confidence: HIGH** — argparse is the standard library choice; no third-party CLI framework is justified for this scope.

### NMEA Checksum

No library needed. Implement inline.

```python
def nmea_checksum(sentence: str) -> str:
    """XOR all bytes between '$' and '*' (exclusive). Return 2-digit uppercase hex."""
    checksum = 0
    for char in sentence:
        checksum ^= ord(char)
    return format(checksum, "02X")
```

Call site:
```python
body = f"GPRMC,{hhmmss}.000,A,0000.0000,N,00000.0000,E,0.0,0.0,{ddmmyy},,,A"
sentence = f"${body}*{nmea_checksum(body)}\r\n"
```

The `\r\n` (CRLF) terminator is required by NMEA 0183 spec. Pass the body string (without `$` and `*`) directly to the checksum function.

**Confidence: HIGH** — NMEA 0183 checksum algorithm is well-documented and stable.

### Exponential Backoff (Reconnect)

Implement inline using stdlib `time`. No third-party library (`tenacity`, `backoff`).

```python
BACKOFF_BASE = 1.0    # seconds
BACKOFF_MAX = 30.0    # seconds cap

delay = BACKOFF_BASE
while not port_open:
    try:
        port = serial.Serial(...)
        delay = BACKOFF_BASE   # reset on success
    except serial.SerialException as e:
        logger.error("Cannot open port %s: %s — retrying in %.0fs", port_name, e, delay)
        time.sleep(delay)
        delay = min(delay * 2, BACKOFF_MAX)
```

**Do not use:**
- `serial.write_timeout` as the primary error detection mechanism — pyserial's `write_timeout` has known spurious `SerialTimeoutException` bugs on POSIX (issues #281, #460 on the pyserial GitHub). Set `write_timeout=2` to prevent indefinite blocking, but catch `SerialException` broadly and treat any write failure as a disconnect event requiring reconnect.

**Confidence: MEDIUM** — exponential backoff pattern is standard; pyserial bug caveats sourced from issue tracker.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Serial | pyserial 3.5 | pyserial-asyncio-fast | asyncio adds complexity for a simple synchronous loop |
| Serial | pyserial 3.5 | serial-asyncio | Same reason; this project has no async I/O |
| Datetime | stdlib datetime | ntplib | Project constraint: OS clock only |
| Datetime | stdlib datetime | pytz | Obsolete; replaced by stdlib zoneinfo; not needed for UTC-only |
| Logging | stdlib logging | structlog | External dependency, JSON logging unneeded for CLI |
| CLI | argparse | click / typer | External dependency, no benefit at this scope |
| Timing | time.sleep + time.time | asyncio / sched | Overcomplicated for a 1Hz loop |
| NMEA parse/gen | inline | pynmea2 / nmeasim | Both are parsing libraries; generation is 3 lines of f-string |

---

## Installation

```bash
# requirements.txt
pyserial==3.5
```

```bash
pip install -r requirements.txt
```

No other runtime dependencies. All other components are Python 3.9 stdlib.

---

## Sources

- [pyserial PyPI page](https://pypi.org/project/pyserial/) — version 3.5, production/stable
- [pyserial GitHub releases](https://github.com/pyserial/pyserial/releases) — 3.5 is latest stable
- [pySerial documentation](https://pyserial.readthedocs.io/en/latest/pyserial.html) — Serial constructor parameters
- [Python datetime docs](https://docs.python.org/3/library/datetime.html) — `datetime.now(timezone.utc)` pattern
- [datetime.utcnow() deprecation](https://blog.miguelgrinberg.com/post/it-s-time-for-a-change-datetime-utcnow-is-now-deprecated) — deprecated Python 3.12, `datetime.UTC` requires 3.11+
- [datetime.UTC vs timezone.utc compatibility](https://github.com/crewAIInc/crewAI/pull/2172) — `timezone.utc` needed for Python < 3.11
- [Python signal docs](https://docs.python.org/3/library/signal.html) — flag-based handler pattern, threading constraints
- [macOS /dev/cu vs /dev/tty](https://www.codegenes.net/blog/what-s-the-difference-between-dev-tty-and-dev-cu-on-macos/) — cu does not block on DCD
- [NMEA checksum algorithm](https://code.activestate.com/recipes/576789-nmea-sentence-checksum/) — XOR between $ and *
- [pyserial write_timeout POSIX bugs](https://github.com/pyserial/pyserial/issues/281) — spurious SerialTimeoutException on POSIX
- [nmea-gps-emulator reference project](https://github.com/luk-kop/nmea-gps-emulator) — prior art; uses pyserial for NMEA serial output
