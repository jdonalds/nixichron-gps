# Feature Landscape: NixiChron GPS NMEA Emulator

**Domain:** Serial time emulator feeding a Nixie tube clock via RS-232
**Researched:** 2026-04-09
**Overall confidence:** HIGH (project scope is tightly defined; NMEA 0183 standard is stable)

---

## Table Stakes

Features the clock will not work without. Missing any one of these = the NixiChron displays
nothing or shows garbled time.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| `$GPRMC` sentence generation | The NixiChron parser reads exactly this sentence type. No other sentence type is accepted. | Low | Format: `$GPRMC,hhmmss.ss,A,llll.ll,a,yyyyy.yy,a,x.x,x.x,ddmmyy,x.x,a*hh<CR><LF>` |
| Status field `A` (Active) | Clock ignores sentences where field 2 is `V` (Void/warning). Must always emit `A`. | Low | Emulator always has valid time — `V` is never appropriate here. |
| UTC time field (`hhmmss.ss`) | Primary data the clock consumes. Wrong format = no lock. | Low | `datetime.now(timezone.utc)` provides this. Fractional seconds `.00` is acceptable. |
| Date field (`ddmmyy`) | The NixiChron stores date alongside time. Required field — cannot be empty. | Low | Same UTC source as time field. |
| XOR checksum (`*HH`) | NMEA 0183 mandates checksum on `$GPRMC`. Most clock parsers silently reject invalid checksums. | Low | XOR of all bytes between `$` and `*`, rendered as two uppercase hex digits. |
| `<CR><LF>` line termination | NMEA 0183 standard line ending. Missing or wrong terminator causes sentence framing failures. | Low | `\r\n` — not just `\n`. |
| 4800 baud, 8N1, no flow control | Fixed by the NixiChron hardware. No negotiation. Wrong baud = no data decoded. | Low | pyserial: `Serial(port, 4800, bytesize=8, parity='N', stopbits=1, xonxoff=False, rtscts=False)` |
| RS-232 voltage levels | NixiChron expects ±12V signals, not 3.3V TTL. The USB-to-RS232 adapter handles this — the software must not try to set voltage levels, only open the port correctly. | Low | Not a software concern once adapter is used correctly. |
| One sentence per second | NixiChron expects exactly 1 Hz. Gaps > 2s may cause it to drop lock; faster rates may confuse the parser. | Medium | NMEA standard requires interval ≤ 2 s. The clock likely uses 1 Hz as the steady-state expectation. |
| Top-of-second alignment | The sentence must arrive near the second boundary so displayed time is accurate. Consistent drift of even 0.5 s makes the clock visibly lag. | Medium | Target: sentence transmission begins within ~100ms of the UTC second boundary. `time.sleep` with drift correction (compute sleep = 1.0 - fractional_seconds) achieves this reliably for a 1 Hz emitter. |
| Dummy position fields | Fields 3–8 (lat, N/S, lon, E/W, speed, course) must be present in the sentence even if zeroed, because the parser counts comma-delimited fields by position. Leaving fields absent shifts all subsequent fields. | Low | Use `0000.0000,N,00000.0000,E,0.0,0.0` or similar. Magnetic variation fields 10–11 may be left empty. |
| Configurable serial port | macOS assigns `/dev/cu.usbserial-*` dynamically. Linux uses `/dev/ttyUSB0`. Hard-coded path breaks on first deployment. | Low | CLI arg `--port` with env var fallback `GPS_PORT`, default `/dev/ttyUSB0`. |
| Python 3.9+ compatibility | Host machines may run stock Python from package managers. No walrus operator in parse paths, no `match/case`, no `X \| Y` union types. | Low | Affects syntax only; no architectural impact. |

---

## Differentiators

Features that make the emulator reliable, debuggable, and maintainable beyond initial bring-up.
The clock will work without these; operations and diagnostics will suffer without them.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| `--dry-run` mode | Lets you verify sentence format and checksum on any machine before connecting real hardware. Essential for development without the clock present. | Low | Print to stdout instead of opening serial port. Sentences look identical to live output. |
| `--self-test` mode | Generate N sentences (default 5), compute checksums internally, verify they match, print PASS/FAIL, exit non-zero on failure. Catches regressions after edits. | Low | No serial port required. Run in CI or before deployment. |
| Structured logging (DEBUG / ERROR) | `DEBUG` logs each emitted sentence (for tracing what the clock received). `ERROR` logs serial failures. Separates signal from noise in production. | Low | Use Python's `logging` module, not `print`. Allows log level to be set by CLI flag or env var. |
| Exponential backoff on serial disconnect | USB adapters detach and reattach (cable wiggle, OS re-enumeration). Without reconnect logic the daemon dies and the clock stops. With backoff: retry 1s, 2s, 4s, 8s… capped at 30s. | Medium | `pyserial` `SerialException` triggers retry loop. Log each attempt at WARN level. On reconnect, log INFO and resume normal operation. |
| SIGTERM / SIGINT handling | systemd sends SIGTERM on `systemctl stop`. Without a handler the port may not be closed cleanly, leaving the USB adapter in a locked state. | Low | Register `signal.signal(SIGTERM, handler)` and `signal.signal(SIGINT, handler)`. Handler sets a stop event, main loop exits, port is closed. |
| Systemd unit file template | Running as a long-lived daemon on Linux requires a unit file. Providing a template (with `%i` instance variable for port) avoids per-user hand-crafting. | Low | Ship as `nixichron-gps.service`. Not auto-installed — documented in README for manual placement. Include `Restart=on-failure` and `RestartSec=5`. |
| Mode indicator field (`A`) | NMEA 2.3+ adds an optional 12th field: `A` = Autonomous. Some newer clock firmwares check this; older ones ignore it. Including it costs nothing and improves compatibility. | Low | Append `,A` before `*HH` checksum: `$GPRMC,...,A*HH`. Does not break NMEA 2.2 parsers since it is after the checksum delimiter in older parsers' view. |
| Sentence-level timing drift correction | Naive `time.sleep(1.0)` accumulates drift (each sleep wakes slightly late). A corrected loop computes `sleep_until = now + 1.0` and sleeps `sleep_until - time.time()` each cycle. Keeps the emitter phase-locked to the system clock over hours. | Low | Prevents the clock drifting forward by several seconds per hour of uptime. |
| ASCII wiring diagram in README | The mini-DIN connector pinout is non-obvious and one wrong wire (pin 2, +5V rail) can damage equipment. A clear diagram embedded in the README prevents mis-wiring on every new install. | Low | Include DB9 ↔ 6-pin mini-DIN mapping with explicit "DO NOT CONNECT" callout for pin 2. |
| Troubleshooting guide in README | macOS device naming (`/dev/cu.*` vs `/dev/tty.*`) and permissions (`dialout` group on Linux) are the most common failure modes. Documenting them avoids repeated first-boot debugging. | Low | Cover: device not found, permission denied, no lock on clock, clock shows wrong time. |

---

## Anti-Features

Things to deliberately NOT build. Each one adds complexity without improving the core outcome.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| NTP client library (`ntplib`) | The host OS is already NTP-disciplined. Adding `ntplib` introduces a second clock source, a network dependency, and a new failure mode (NTP server unreachable). | Use `datetime.now(timezone.utc)` which reads the already-synced OS clock. |
| Other NMEA sentence types (`$GPGGA`, `$GPGSA`, `$GPGSV`, `$GPZDA`, etc.) | The NixiChron parses only `$GPRMC`. Extra sentences consume baud rate budget (at 4800 baud there is limited headroom), add complexity, and provide no benefit. | Emit exactly one `$GPRMC` per second. |
| Bidirectional serial (reading from clock) | The NixiChron does not send data back over the GPS port. Attempting to read from the port wastes CPU and complicates the port lifecycle. | Open the serial port write-only (or write-first — pyserial opens bidirectional but never call `read()`). |
| GUI or web interface | This is a headless background daemon. A GUI adds a display dependency, makes remote/SSH operation impossible, and serves no user need. | CLI flags + structured logs provide all necessary interaction. |
| macOS launchd plist (generated) | macOS users are likely developers who will run the script manually or via a login item. The launchd plist format is verbose and platform-specific; maintaining it alongside the systemd unit doubles the daemon-management surface area. | Document manual invocation for macOS in the README. Provide the systemd unit for Linux. |
| Multi-clock / multi-port support | This design is for one clock on one serial port. Supporting N clocks requires threading or async, complicates the reconnect logic, and has no known use case. | Single port, single clock. Run multiple script instances if ever needed. |
| Configurable baud rate | The NixiChron requires exactly 4800 baud. Making baud configurable implies it is a valid variable, which it is not. A user who changes it breaks the clock. | Hard-code 4800 in the serial open call. Document this explicitly. |
| Position accuracy / movement simulation | GPS emulators that simulate position movement (lat/lon change over time) are useful for testing mapping software, not clocks. The NixiChron only uses time fields. | Static dummy position (e.g., 0°N 0°E or any fixed coord). |
| Interactive runtime commands | Emulators like `luk-kop/nmea-gps-emulator` allow changing speed/heading at runtime via keyboard. For a clock feeder this is meaningless and adds a REPL dependency. | Stateless loop — no runtime interaction. |
| Checksum validation of received data | The emulator sends to the clock; the clock does not send back. There is nothing to validate on the receive side. | Not applicable — transmit only. |

---

## Feature Dependencies

```
$GPRMC sentence generation
  └─► XOR checksum calculation         (sentence is invalid without it)
  └─► UTC time field                   (primary payload)
  └─► Date field                       (required field, same source as time)
  └─► Dummy position fields            (field-count correctness)
  └─► <CR><LF> termination            (framing)

Top-of-second alignment
  └─► Drift correction loop            (sustained accuracy over time)
  └─► $GPRMC sentence generation       (what gets sent at each boundary)

Serial port open (4800/8N1)
  └─► Exponential backoff reconnect    (resilience after disconnect)
  └─► SIGTERM/SIGINT handler           (clean shutdown closes port)

--dry-run mode
  └─► $GPRMC sentence generation       (same sentences, stdout not port)
  └─► XOR checksum                     (visible in output for verification)

--self-test mode
  └─► $GPRMC sentence generation
  └─► XOR checksum                     (tests both generation and verification)
```

---

## MVP Recommendation

Prioritize (must ship together — clock won't work otherwise):

1. `$GPRMC` sentence construction with correct field layout and `<CR><LF>`
2. XOR checksum calculation (two uppercase hex digits)
3. Top-of-second alignment with drift correction (sleep-until-next-second loop)
4. Serial port open at 4800/8N1 via pyserial
5. SIGTERM/SIGINT handler with clean port close
6. `--dry-run` flag (needed for any development without hardware)
7. `--self-test` flag (needed to verify correctness before connecting the clock)
8. DEBUG/ERROR logging via `logging` module
9. Exponential backoff reconnect on serial failure

Defer to later (after the clock is demonstrably working):

- Systemd unit file — useful for Linux deployment but not needed to prove the concept
- README / wiring diagram — needed before handing off to others, not before initial test
- Mode indicator field (field 12, `A`) — include from the start since it is one token; only defer if it causes an unexpected parse failure on the target clock firmware

---

## NixiChron-Specific Lock Behaviour

Based on research (MEDIUM confidence — no official NixiChron firmware docs found publicly):

- The clock expects `$GPRMC` with status `A` and valid UTC+date fields.
- It treats `V`-status sentences as "no signal" — likely shows dashes or last-known time.
- It does not need multiple consecutive valid sentences to "lock"; the first valid `A`-status sentence should update the display.
- The 4800 baud rate is confirmed fixed by the Jeff Thomas design (matched by Haicom HI-204III module it was designed for, and corroborated by the neonixie-l mailing list discussion).
- The mini-DIN pin 2 (+5V rail) must never be connected — the clock powers the GPS module through this pin and connecting it to the RS-232 adapter would short the clock's supply rail.

---

## Sources

- [NMEA Revealed — gpsd project](https://gpsd.gitlab.io/gpsd/NMEA.html) — authoritative NMEA 0183 field documentation
- [APRS NMEA sentence reference](https://aprs.gids.nl/nmea/) — $GPRMC field layout
- [Trimble NMEA RMC reference](https://receiverhelp.trimble.com/alloy-gnss/en-us/NMEA-0183messages_RMC.html) — optional field handling, mode indicator
- [NTP.org NMEA driver](https://www.ntp.org/documentation/drivers/driver20/) — timing and sentence frequency requirements
- [neonixie-l mailing list](https://www.mail-archive.com/neonixie-l@googlegroups.com/msg30503.html) — NixiChron GPS module identification (Haicom HI-204III)
- [luk-kop/nmea-gps-emulator](https://github.com/luk-kop/nmea-gps-emulator) — reference implementation for feature comparison
- [nmeasim on PyPI](https://pypi.org/project/nmeasim/) — Python NMEA simulation library (considered, not adopted)
- [Python time.sleep accuracy](https://www.pythontutorials.net/blog/how-accurate-is-python-s-time-sleep/) — timing precision analysis for 1 Hz emitter
