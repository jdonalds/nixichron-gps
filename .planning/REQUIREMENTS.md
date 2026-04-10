# Requirements: NixiChron GPS Emulator

**Defined:** 2026-04-09
**Core Value:** The NixiChron clock displays accurate UTC time from the host's NTP-synced system clock, without a real GPS module.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### NMEA Sentence Generation

- [x] **NMEA-01**: Script generates valid `$GPRMC` sentences with all 13 fields including NMEA 2.3 mode indicator `A`
- [x] **NMEA-02**: XOR checksum computed over all bytes between `$` and `*` (exclusive), formatted as two uppercase hex digits
- [x] **NMEA-03**: UTC time field formatted as `hhmmss.00` from `datetime.now(timezone.utc)`
- [x] **NMEA-04**: UTC date field formatted as `ddmmyy` from same UTC source
- [x] **NMEA-05**: Status field is always `A` (Active) — never `V`
- [x] **NMEA-06**: Dummy position fields present: `0000.0000,N,00000.0000,E`
- [x] **NMEA-07**: Speed `0.0`, course `0.0`, empty magnetic variation fields
- [x] **NMEA-08**: Sentence terminated with `<CR><LF>` (`\r\n`)
- [x] **NMEA-09**: Only `$GPRMC` sentences emitted — no other sentence types (GGA/GSA/GSV/VTG will overflow the PIC buffer and break the clock)

### Timing

- [x] **TIME-01**: Sentences emitted at exactly 1 Hz, aligned to the UTC second boundary
- [x] **TIME-02**: Deadline-based timing loop (not naive `sleep(1)`) to prevent drift accumulation
- [x] **TIME-03**: The `$` character (leading edge = clock's 1 PPS trigger) should be transmitted as close to the second boundary as possible

### Serial Communication

- [ ] **SER-01**: Serial port opened at 4800 baud, 8N1, no flow control (xonxoff=False, rtscts=False)
- [ ] **SER-02**: Serial port configurable via `--port` CLI arg, `GPS_PORT` env var, or default `/dev/ttyUSB0`
- [ ] **SER-03**: Graceful handling of serial port disconnects with exponential backoff retry (1s, 2s, 4s... capped at 30s)
- [ ] **SER-04**: Reconnect logged at WARNING level; successful reconnect logged at INFO level

### Signal Handling

- [ ] **SIG-01**: SIGTERM and SIGINT caught cleanly — sets a shutdown flag, main loop exits
- [ ] **SIG-02**: Serial port closed in `finally` block on shutdown (prevents locked USB adapter state)

### CLI Interface

- [x] **CLI-01**: `--port` argument to specify serial device
- [x] **CLI-02**: `--dry-run` flag prints sentences to stdout instead of serial port
- [x] **CLI-03**: `--self-test` flag generates 5 sentences, validates each checksum against independent implementation, exits with pass/fail
- [x] **CLI-04**: `--verbose` or `-v` flag sets log level to DEBUG (default: INFO)

### Logging

- [x] **LOG-01**: Each sent sentence logged at DEBUG level
- [ ] **LOG-02**: Serial errors logged at ERROR level
- [x] **LOG-03**: Uses Python `logging` module (not print statements)

### Deployment Artifacts

- [ ] **DEPLOY-01**: `requirements.txt` containing `pyserial==3.5`
- [ ] **DEPLOY-02**: `nixichron-gps.service` systemd unit file template with placeholders for user and script path
- [ ] **DEPLOY-03**: Systemd unit: `Restart=on-failure`, depends on `network-online.target` and `time-sync.target`, runs as non-root user
- [ ] **DEPLOY-04**: `README.md` with ASCII wiring diagram (DB9 pin 3 TX → mini-DIN pin 5 RX, DB9 pin 5 GND → mini-DIN pin 1 GND, mini-DIN pin 2 DO NOT CONNECT, mini-DIN pin 4 leave floating)
- [ ] **DEPLOY-05**: README install steps: `pip install -r requirements.txt`, copy systemd unit, `systemctl enable --now`
- [ ] **DEPLOY-06**: README troubleshooting: clock not locking (check TX/GND wiring, check permissions, add user to dialout group), clock counting from 00:00 (status field not A, or non-UTC time), verify NMEA with `cat` loopback, macOS `cu.*` vs `tty.*` device naming

### Validation

- [x] **VAL-01**: `python nixichron_gps.py --self-test` passes (5 sentences, all checksums valid)
- [x] **VAL-02**: `python nixichron_gps.py --dry-run` for 5 seconds produces correctly formatted sentences with valid checksums and current UTC time
- [x] **VAL-03**: At least one checksum manually verified against known-good calculator

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### ESP32 Port

- **ESP-01**: Port core NMEA logic to MicroPython/C for ESP32 with NTP time source
- **ESP-02**: Direct RS-232 output via MAX3232 breakout (no USB adapter needed)
- **ESP-03**: Wi-Fi configuration via captive portal or hardcoded credentials

### Enhanced Monitoring

- **MON-01**: Optional heartbeat log every N minutes confirming sentences still being sent
- **MON-02**: Optional metrics (sentences sent, reconnects, uptime) exposed via simple HTTP endpoint

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| NTP client library (ntplib) | OS clock is already NTP-synced; adding ntplib introduces second clock source and network failure mode |
| Other NMEA sentences ($GPGGA, $GPGSA, etc.) | Will overflow the PIC buffer and break the clock — Jeff Thomas designed the firmware for $GPRMC only |
| Bidirectional serial (reading from clock) | Clock does not send data back over GPS port |
| GUI or web interface | Headless daemon; CLI + logs provide all needed interaction |
| macOS launchd plist | macOS users run manually or via login item; systemd unit covers Linux |
| Multi-clock / multi-port support | Single clock, single port; run multiple instances if needed |
| Configurable baud rate | NixiChron requires exactly 4800; making it configurable implies it's variable |
| Position simulation / movement | Clock only uses time and date fields; position is ignored |
| Real-time interactive commands | Stateless 1 Hz loop; no runtime interaction needed |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| NMEA-01 | Phase 1 | Complete |
| NMEA-02 | Phase 1 | Complete |
| NMEA-03 | Phase 1 | Complete |
| NMEA-04 | Phase 1 | Complete |
| NMEA-05 | Phase 1 | Complete |
| NMEA-06 | Phase 1 | Complete |
| NMEA-07 | Phase 1 | Complete |
| NMEA-08 | Phase 1 | Complete |
| NMEA-09 | Phase 1 | Complete |
| TIME-01 | Phase 3 | Complete |
| TIME-02 | Phase 3 | Complete |
| TIME-03 | Phase 3 | Complete |
| SER-01 | Phase 5 | Pending |
| SER-02 | Phase 5 | Pending |
| SER-03 | Phase 5 | Pending |
| SER-04 | Phase 5 | Pending |
| SIG-01 | Phase 4 | Pending |
| SIG-02 | Phase 4 | Pending |
| CLI-01 | Phase 2 | Complete |
| CLI-02 | Phase 2 | Complete |
| CLI-03 | Phase 2 | Complete |
| CLI-04 | Phase 2 | Complete |
| LOG-01 | Phase 2 | Complete |
| LOG-02 | Phase 2 | Pending |
| LOG-03 | Phase 2 | Complete |
| DEPLOY-01 | Phase 6 | Pending |
| DEPLOY-02 | Phase 6 | Pending |
| DEPLOY-03 | Phase 6 | Pending |
| DEPLOY-04 | Phase 6 | Pending |
| DEPLOY-05 | Phase 6 | Pending |
| DEPLOY-06 | Phase 6 | Pending |
| VAL-01 | Phase 1 | Complete |
| VAL-02 | Phase 1 | Complete |
| VAL-03 | Phase 1 | Complete |

**Coverage:**
- v1 requirements: 34 total
- Mapped to phases: 34
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-09*
*Last updated: 2026-04-09 after roadmap creation*
