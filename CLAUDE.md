<!-- GSD:project-start source:PROJECT.md -->
## Project

**NixiChron GPS Emulator**

A Python script that emulates a GPS receiver by sending NMEA $GPRMC sentences over a serial port to a Jeff Thomas NixiChron Nixie tube clock. Instead of using a real GPS module, it reads the host machine's NTP-synced system clock and formats UTC time into standard NMEA sentences at 1-second intervals. The NixiChron clock reads these sentences and displays the time.

**Core Value:** The clock displays accurate UTC time, synchronized to the host's NTP-disciplined system clock, without requiring a real GPS module.

### Constraints

- **Python 3.9+**: Must work without newer syntax (no match/case, no `X | Y` union types)
- **Single script**: All logic in one file `nixichron_gps.py` — no package structure
- **No NTP library**: System clock only, via `datetime.now(timezone.utc)`
- **4800 baud fixed**: Not configurable — NixiChron expects exactly 4800
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Runtime
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.9+ | Runtime | Project constraint. All stdlib modules below are available in 3.9. No third-party runtime required beyond pyserial. |
### Serial Communication
| Library | Version | Purpose | Why |
|---------|---------|---------|-----|
| pyserial | 3.5 | Serial port I/O | The only maintained, cross-platform Python serial library. Production/Stable status. Handles RS-232 over USB adapters on macOS and Linux. Version 3.5 is the latest stable release (November 2020); the project has not released a 3.6. No viable alternative exists. |
### Datetime / UTC Handling
- `datetime.utcnow()` — deprecated in Python 3.12, returns a naive datetime (no tzinfo), incorrect for explicit UTC work.
- `datetime.UTC` — alias for `timezone.utc` added in Python 3.11; breaks on Python 3.9 and 3.10.
- `ntplib` or any NTP client — the project constraint excludes this; the host OS clock is already NTP-disciplined.
- `pytz` — obsolete; replaced by stdlib `zoneinfo` in 3.9. Not needed here because the output is always UTC.
- `zoneinfo` — not needed; this application only ever uses UTC.
### Timing — Top-of-Second Alignment
- `time.monotonic()` alone — monotonic clock is useful for measuring elapsed time but does not give you wall-clock seconds. The `%` modulo trick requires `time.time()` (wall clock) to align to real UTC seconds.
- `asyncio` event loop — adds complexity with no benefit for a single-loop, single-port script.
- `py-abs-sleep` or other third-party timing libraries — unnecessary for this use case.
### Signal Handling
- `KeyboardInterrupt` as the sole shutdown mechanism — SIGTERM (systemd stop, `kill`) will not trigger it.
- `atexit` module as the only mechanism — `atexit` runs on normal exit but may not run on SIGTERM without the flag pattern.
- Socket-pair pattern (from Python signal docs) — correct for event-loop programs, overkill for a simple while loop.
### Logging
- `structlog` — excellent library for services, but adds a dependency and JSON output is unnecessary for a single-user CLI tool.
- `print()` — use only for `--dry-run` sentence output (which is intentional stdout, not logging).
- Root logger `logging.warning(...)` calls — always use a named logger via `getLogger(__name__)`.
### CLI Argument Parsing
- `click` — decorator-based, cleaner DX, but adds a dependency. `argparse` is stdlib and sufficient.
- `typer` — requires Python 3.6+ and type annotations; adds a dependency for no benefit here.
### NMEA Checksum
### Exponential Backoff (Reconnect)
- `serial.write_timeout` as the primary error detection mechanism — pyserial's `write_timeout` has known spurious `SerialTimeoutException` bugs on POSIX (issues #281, #460 on the pyserial GitHub). Set `write_timeout=2` to prevent indefinite blocking, but catch `SerialException` broadly and treat any write failure as a disconnect event requiring reconnect.
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
## Installation
# requirements.txt
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
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
