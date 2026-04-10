# NixiChron GPS Emulator

## What This Is

A Python script that emulates a GPS receiver by sending NMEA $GPRMC sentences over a serial port to a Jeff Thomas NixiChron Nixie tube clock. Instead of using a real GPS module, it reads the host machine's NTP-synced system clock and formats UTC time into standard NMEA sentences at 1-second intervals. The NixiChron clock reads these sentences and displays the time.

## Core Value

The clock displays accurate UTC time, synchronized to the host's NTP-disciplined system clock, without requiring a real GPS module.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Single Python script `nixichron_gps.py` that generates and sends $GPRMC sentences
- [ ] Configurable serial port via CLI arg or env var (default `/dev/ttyUSB0`)
- [ ] Serial config: 4800 baud, 8N1, no flow control, RS-232 levels
- [ ] Sentences sent every second, aligned to the top-of-second boundary
- [ ] Correct $GPRMC format with UTC time, dummy position, status A, mode A
- [ ] XOR checksum calculated correctly (between `$` and `*`, two uppercase hex digits)
- [ ] Uses OS system clock (`datetime.now(timezone.utc)`) — no NTP library
- [ ] Logging: DEBUG for sent sentences, ERROR for failures
- [ ] Graceful serial disconnect handling with exponential backoff (capped 30s)
- [ ] Clean SIGTERM/SIGINT handling with port closure
- [ ] `--dry-run` flag: print sentences to stdout instead of serial port
- [ ] `--self-test` flag: generate 5 sentences, validate checksums, exit
- [ ] `requirements.txt` with pyserial
- [ ] `nixichron-gps.service` systemd unit file (template with placeholders)
- [ ] `README.md` with ASCII wiring diagram, install steps, troubleshooting

### Out of Scope

- NTP client library (ntplib) — OS clock is already NTP-synced
- Other NMEA sentence types ($GPGGA, $GPGSA, etc.) — NixiChron only needs $GPRMC
- Bidirectional serial communication — clock doesn't send data back
- macOS launchd plist — systemd unit provided as reference; macOS runs manually or via login item
- GUI or web interface — CLI-only tool
- Multi-clock support — single serial port, single clock

## Context

- **Target clock:** Jeff Thomas NixiChron with 6-pin mini-DIN GPS input
- **Connection:** USB-to-RS232 adapter (DB9) → mini-DIN cable to clock
- **Signal levels:** Full RS-232 (+/-12V), not TTL
- **Host OS:** macOS (primary), Linux (secondary/future)
- **Wiring (DB9 → 6-pin mini-DIN):**
  - DB9 pin 3 (TX) → mini-DIN pin 5 (Clock RX / "puck TX")
  - DB9 pin 5 (GND) → mini-DIN pin 1 (Ground)
  - mini-DIN pin 2: **DO NOT CONNECT** — clock's +5V rail
  - mini-DIN pin 4: Leave floating
- **Python version:** 3.9+
- **Serial device on macOS:** typically `/dev/tty.usbserial-*` or `/dev/cu.usbserial-*`

## Constraints

- **Python 3.9+**: Must work without newer syntax (no match/case, no `X | Y` union types)
- **Single script**: All logic in one file `nixichron_gps.py` — no package structure
- **No NTP library**: System clock only, via `datetime.now(timezone.utc)`
- **4800 baud fixed**: Not configurable — NixiChron expects exactly 4800

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use OS clock, not ntplib | Host is already NTP-synced; adding ntplib adds complexity and a failure mode | — Pending |
| RS-232 via USB adapter | NixiChron expects RS-232 voltage levels; USB adapter handles level shifting | — Pending |
| Single script, no package | Simplicity — one file to deploy, one file to understand | — Pending |
| Systemd unit as template only | Primary target is macOS; systemd file provided for Linux users | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-09 after initialization*
