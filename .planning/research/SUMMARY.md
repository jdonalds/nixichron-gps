# Project Research Summary

**Project:** NixiChron GPS Emulator (`nixichron_gps.py`)
**Domain:** Python CLI serial-port NMEA time emitter for a Nixie tube clock
**Researched:** 2026-04-09
**Confidence:** HIGH

## Executive Summary

The NixiChron GPS emulator is a single-file Python CLI daemon that generates `$GPRMC` NMEA sentences once per second over a USB-to-RS-232 serial adapter, feeding a Jeff Thomas NixiChron Nixie tube clock that expects GPS time sync. The project has exactly one external dependency (`pyserial 3.5`); all other requirements are covered by the Python 3.9 standard library. The recommended approach is a flat script with clearly separated functional sections — no classes, no async, no framework — because the problem is a simple 1 Hz synchronous loop with one I/O surface.

The key risk is silent failure: nearly all mistakes in this domain produce a clock that never locks rather than an error message. Wrong checksum byte range, lowercase hex digits, missing `\r\n` terminator, status field set to `V`, local time instead of UTC, and naive `time.sleep(1)` drift are the six implementation errors most likely to cause the clock to silently ignore sentences. The mitigation is a `--dry-run` flag that prints sentences to stdout for visual inspection and a `--self-test` flag that validates the full generation-plus-checksum pipeline without requiring hardware.

The hardware constraint that defines the entire project is fixed: 4800 baud, 8N1, no flow control, one `$GPRMC` per second, status field always `A`. Nothing about these values is configurable or negotiable. The build order follows a strict dependency chain: checksum calculator first (no dependencies, immediately testable), then NMEA sentence builder, then self-test runner, then CLI wiring, then the timing loop, then the main loop with dry-run, and finally real serial port I/O with reconnect logic.

## Key Findings

### Recommended Stack

The entire project runs on Python 3.9+ with a single external package. Python 3.9 is the floor — do not use `match/case`, `X | Y` union types, or `datetime.UTC` (requires 3.11). All timing, logging, argument parsing, signal handling, and NMEA checksum generation are pure stdlib. pyserial 3.5 is the only viable cross-platform serial library and has no serious alternatives.

**Core technologies:**
- **Python 3.9+**: runtime — project constraint, all needed stdlib modules present
- **pyserial 3.5**: serial port I/O — only maintained cross-platform Python serial library
- **stdlib `datetime` + `timezone.utc`**: UTC time source — `datetime.now(timezone.utc)`, never `datetime.utcnow()` or `datetime.UTC`
- **stdlib `time`**: deadline-based sleep loop — `time.time()` for wall-clock alignment, `time.sleep()` for sub-second duration
- **stdlib `signal`**: clean shutdown — flag-based handler, no I/O inside the handler
- **stdlib `logging`**: structured output — named logger, DEBUG per sentence, ERROR on failures
- **stdlib `argparse`**: CLI — `--port`, `--dry-run`, `--self-test`, `-v`

### Expected Features

**Must have (table stakes — clock will not work without these):**
- `$GPRMC` sentence generation with correct 12-field layout and CRLF termination
- Status field hard-coded to `A` (Active) — never `V`
- UTC time field (`hhmmss.00`) sourced from `datetime.now(timezone.utc)`
- Date field (`ddmmyy` — day first, not ISO order)
- XOR checksum as two uppercase hex digits (`02X` format)
- `\r\n` line terminator (not `\n`)
- Serial port opened at 4800 baud, 8N1, no flow control
- Exactly one sentence per second with top-of-second alignment (deadline sleep, not naive `time.sleep(1)`)
- Dummy position fields present (zeroed) so field offsets are correct
- Configurable serial port via `--port` CLI flag with env-var fallback

**Should have (operational reliability):**
- `--dry-run` mode — stdout output, no serial port required; essential for development
- `--self-test` mode — generate and validate sentences, exit 0/1, no hardware needed
- Exponential backoff reconnect on `SerialException` (1s → 2s → 4s … cap 30s)
- SIGTERM/SIGINT handler with clean port close in `finally` block
- DEBUG/ERROR logging via `logging` module
- Mode indicator field 12 (`A` = Autonomous) for NMEA 2.3 compatibility

**Defer (after clock is demonstrably working):**
- systemd unit file — useful for Linux deployment, not needed for initial validation
- README wiring diagram — needed before handoff, not before first test
- macOS launchd plist — out of scope; document manual invocation instead

**Deliberate anti-features (do not build):**
- NTP client (`ntplib`) — OS clock is already disciplined
- Additional NMEA sentence types (`$GPGGA`, `$GPZDA`, etc.) — NixiChron reads only `$GPRMC`
- Configurable baud rate — 4800 is a hardware fixed value; making it configurable invites breakage
- Bidirectional serial reads — NixiChron sends nothing back
- GUI or web interface — headless daemon only

### Architecture Approach

The script is intentionally a singleton flat file with ten clearly separated functional sections and no classes. Dependencies form a strict layer stack: checksum calculator at the bottom, NMEA builder on top of it, self-test runner and CLI parser above that, timing helper and signal handler alongside, serial port abstraction with backoff on top, and `main()` as the integration point. The dry-run abstraction is a single boolean at the write dispatch point in `main()` — both paths accept the same `bytes` object from the NMEA builder. Port close always lives in a `finally` block, never inside the signal handler.

**Major components:**
1. **Checksum calculator** — XOR bytes between `$` and `*`; returns `str` (2 uppercase hex chars)
2. **NMEA sentence builder** — assembles `$GPRMC` fields from a UTC `datetime`; calls checksum; returns `bytes` with `\r\n`
3. **Top-of-second sleep helper** — computes deadline from `datetime.microsecond`; calls `time.sleep()`
4. **Signal handler + shutdown flag** — sets `_shutdown = True` on SIGTERM/SIGINT; no I/O in handler
5. **Serial port abstraction + backoff** — opens at 4800/8N1; wraps `write()` in try/except; exponential retry
6. **Self-test runner** — generates 5+ sentences, verifies checksums, exits 0/1; no port needed
7. **CLI parser + logging setup** — `argparse`; configures log level; routes to self-test or main loop
8. **Main loop** — polls `_shutdown`; sleeps to boundary; builds sentence; dispatches to port or stdout

### Critical Pitfalls

1. **Wrong XOR checksum range** — include `$` or miss the last byte before `*` and every sentence is silently rejected. Use `sentence[1:sentence.index('*')]` as the input range. Verify with `--self-test` against known expected values.

2. **Status field `V` instead of `A`** — the single most common reason a syntactically correct emulator fails to drive a GPS clock. Hard-code `A`; never make it dynamic. Verify in `--self-test`.

3. **Local time instead of UTC** — `datetime.now()` without `timezone.utc` sends local time labeled as UTC. The clock will display correct format but wrong time. Always use `datetime.now(timezone.utc)`. Compare `--dry-run` output against `date -u`.

4. **Naive `time.sleep(1)` drift** — execution overhead accumulates. After an hour the emitter is measurably late. Use a deadline-based loop: `next_tick = math.ceil(time.time()); time.sleep(max(0, next_tick - time.time()))`.

5. **`/dev/tty.usbserial-*` instead of `/dev/cu.usbserial-*` on macOS** — the `tty.*` device blocks `open()` forever waiting for DCD assertion that the NixiChron never sends. Always use `cu.*` on macOS. Document explicitly.

6. **Missing `\r\n` terminator** — Python defaults to `\n`. NMEA requires CR+LF. The clock accumulates malformed frames and never locks. Encode as `(body + '\r\n').encode('ascii')`.

7. **Checksum hex not uppercase or not zero-padded** — use `f'{checksum:02X}'` always. `hex()` and `'%x'` produce lowercase; NMEA requires uppercase.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Core Sentence Engine
**Rationale:** Checksum calculator and NMEA builder have no external dependencies and are testable immediately. Everything else depends on them. Getting these right first, with `--self-test` validation, eliminates the most common silent-failure modes before any I/O is involved.
**Delivers:** `nmea_checksum()` function, `build_gprmc()` function, `--self-test` runner, all verified against known expected output
**Addresses:** Table-stakes features — correct `$GPRMC` format, `A` status, UTC time, `ddmmyy` date, `\r\n` terminator, uppercase checksum
**Avoids:** Pitfalls 1, 2, 3, 6, 7 (checksum range, status=V, local time, CRLF, lowercase hex) — all caught by self-test before hardware is ever involved

### Phase 2: CLI Shell and Dry-Run Mode
**Rationale:** CLI parser and `--dry-run` complete the hardware-free development surface. Once dry-run works, any machine can be used to visually validate sentence output without the clock present.
**Delivers:** `argparse` setup with `--port`, `--dry-run`, `--self-test`, `-v`; logging configured; `sys.stdout.buffer.write()` dispatch path
**Addresses:** Configurable port, logging, dry-run differentiator feature
**Avoids:** Encoding divergence (both dry-run and real paths use the same `bytes` object)

### Phase 3: Timing Loop
**Rationale:** The top-of-second sleep helper is a pure-stdlib component with no hardware dependency. It can be tested and measured in dry-run mode before any serial port is opened.
**Delivers:** Deadline-based sleep function (`math.ceil(time.time())`), main loop skeleton polling `_shutdown`
**Addresses:** Top-of-second alignment, drift correction
**Avoids:** Pitfall 6 (naive sleep drift)

### Phase 4: Signal Handling and Clean Shutdown
**Rationale:** Signal handlers must be registered before the main loop starts and before the serial port is opened. Establishing the shutdown flag pattern here makes it available for the port lifecycle in the next phase.
**Delivers:** `_handle_signal()` registered for SIGINT and SIGTERM, `_shutdown` flag, `finally` block in `main()`
**Addresses:** SIGTERM/SIGINT differentiator feature
**Avoids:** Pitfall — port locked after Ctrl-C, systemd restart loop

### Phase 5: Serial Port I/O and Reconnect
**Rationale:** This is the only phase requiring hardware (or a loopback device). All prior phases are testable in dry-run. Adding serial port open, write, and exponential backoff reconnect here completes the daemon.
**Delivers:** `serial.Serial` open at 4800/8N1, `write()` wrapped in `SerialException` catch, exponential backoff loop (1s → 30s cap), full end-to-end loop
**Addresses:** Configurable port (uses `--port` from Phase 2), backoff reconnect differentiator
**Avoids:** Pitfalls 4 (`tty.*` vs `cu.*` on macOS), 5 (wrong baud), pyserial `write_timeout` bug (set `write_timeout=2`, catch `SerialException` broadly)

### Phase 6: Deployment Artifacts
**Rationale:** Once the clock is demonstrably working, deployment artifacts become relevant. Systemd unit file and README wiring diagram are low-complexity but high-value for handoff.
**Delivers:** `nixichron-gps.service` systemd unit template, README with wiring diagram (DB9 to mini-DIN), macOS driver troubleshooting, `dialout` group permission note
**Addresses:** Systemd unit and wiring diagram differentiator features
**Avoids:** Pitfall 8 (macOS driver approval process documented), `tty.*` vs `cu.*` documented at install time

### Phase Ordering Rationale

- Phases 1-4 require no hardware at all; this is intentional. The most dangerous bugs (wrong checksum, status=V, local time) are caught in dry-run before the NixiChron is ever connected.
- Phase 5 is last among implementation phases because it is the only one that requires physical hardware or a loopback device; deferring it maximizes development flexibility.
- Phase 6 is explicitly deferred until the clock is confirmed working — documentation of a broken system is waste.
- The build order within each phase mirrors the architecture's layer dependency graph (ARCHITECTURE.md Layer 1-8 order).

### Research Flags

Phases with standard, well-documented patterns (deep research not needed):
- **Phase 1:** NMEA 0183 checksum and `$GPRMC` format are fully specified and stable
- **Phase 2:** `argparse` and `logging` are stdlib with excellent documentation
- **Phase 3:** Deadline-based sleep is established Python practice
- **Phase 4:** Signal flag pattern is in official Python signal docs
- **Phase 6:** systemd unit file structure is standard

Phases that may need hardware validation:
- **Phase 5:** NixiChron firmware behavior on first valid sentence, reconnect timing, and whether the clock tolerates the DTR/RTS toggle on port open — these are MEDIUM-confidence findings. Validate with the actual hardware.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | pyserial 3.5, Python 3.9 stdlib — official docs, no viable alternatives |
| Features | HIGH | NMEA 0183 spec is stable; NixiChron behavior sourced from neonixie-l mailing list (MEDIUM for firmware specifics) |
| Architecture | HIGH | Single-loop synchronous pattern is well-established; all component boundaries are clear |
| Pitfalls | HIGH | Most verified against official NMEA spec, pyserial docs, and community sources |

**Overall confidence:** HIGH

### Gaps to Address

- **NixiChron firmware specifics:** No official public documentation found. Lock behavior (how many valid sentences before display updates, behavior on `V`-status sentences) sourced from neonixie-l mailing list. Validate empirically in Phase 5.
- **macOS Sequoia driver compatibility:** CH340/Prolific adapter support on macOS Sequoia is vendor-dependent and may require a kernel extension not yet available as a dext. Use FTDI-chipset adapters to avoid this. Cannot be resolved without the target hardware.
- **pyserial `write_timeout` POSIX bugs:** Known spurious `SerialTimeoutException` on POSIX (pyserial issues #281, #460). Mitigation is to catch `SerialException` broadly rather than relying on `write_timeout` for error detection. Treat any write failure as a disconnect event.

## Sources

### Primary (HIGH confidence)
- [gpsd NMEA Revealed](https://gpsd.gitlab.io/gpsd/NMEA.html) — authoritative `$GPRMC` field documentation
- [NovAtel OEM7 GPRMC docs](https://docs.novatel.com/OEM7/Content/Logs/GPRMC.htm) — mode indicator field `A`
- [pyserial official docs](https://pyserial.readthedocs.io/en/latest/pyserial.html) — Serial constructor, SerialException
- [Python datetime docs](https://docs.python.org/3/library/datetime.html) — `datetime.now(timezone.utc)` pattern
- [Python signal docs](https://docs.python.org/3/library/signal.html) — flag-based handler pattern
- [Python time docs](https://docs.python.org/3/library/time.html) — monotonic clock, sleep behavior

### Secondary (MEDIUM confidence)
- [neonixie-l mailing list](https://www.mail-archive.com/neonixie-l@googlegroups.com/msg30503.html) — NixiChron GPS module ID (Haicom HI-204III), 4800 baud confirmed
- [pyserial GitHub issues #281, #460](https://github.com/pyserial/pyserial/issues/281) — write_timeout POSIX bugs
- [macOS cu.* vs tty.* behavior](https://www.codegenes.net/blog/what-s-the-difference-between-dev-tty-and-dev-cu-on-macos/) — DCD blocking on tty.*
- [luk-kop/nmea-gps-emulator](https://github.com/luk-kop/nmea-gps-emulator) — prior art reference implementation

### Tertiary (LOW confidence / needs hardware validation)
- NixiChron lock behavior on first valid sentence — inferred from NMEA standard behavior; not confirmed against actual firmware
- macOS Sequoia dext availability for CH340/Prolific chipsets — based on community reports, vendor-specific

---
*Research completed: 2026-04-09*
*Ready for roadmap: yes*
