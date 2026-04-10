# Roadmap: NixiChron GPS Emulator

## Overview

Six phases deliver a single Python daemon that feeds a Jeff Thomas NixiChron Nixie tube clock with $GPRMC sentences over RS-232. The build order is intentionally hardware-free for the first five phases: correctness is proven at the sentence level (Phase 1) before CLI wiring (Phase 2), timing (Phase 3), and signal handling (Phase 4) are added. Serial I/O (Phase 5) is the only phase requiring physical hardware, placed last so all prior work can be validated in dry-run mode. Deployment artifacts (Phase 6) follow only after the clock is confirmed working.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Core Sentence Engine** - Generate correct $GPRMC sentences with valid checksums, verified by --self-test (completed 2026-04-10)
- [ ] **Phase 2: CLI Shell and Logging** - Wire argparse, logging, and --dry-run so sentences can be inspected without hardware
- [ ] **Phase 3: Timing Loop** - Implement deadline-based 1 Hz loop aligned to UTC second boundary
- [ ] **Phase 4: Signal Handling** - Register SIGTERM/SIGINT handler and guarantee clean port close on shutdown
- [ ] **Phase 5: Serial I/O and Reconnect** - Open serial port at 4800/8N1 and add exponential backoff reconnect
- [ ] **Phase 6: Deployment Artifacts** - Ship requirements.txt, systemd unit template, and README with wiring diagram

## Phase Details

### Phase 1: Core Sentence Engine
**Goal**: The script generates syntactically correct $GPRMC sentences with valid XOR checksums, proven correct by --self-test before any serial port is opened
**Depends on**: Nothing (first phase)
**Requirements**: NMEA-01, NMEA-02, NMEA-03, NMEA-04, NMEA-05, NMEA-06, NMEA-07, NMEA-08, NMEA-09, VAL-01, VAL-02, VAL-03
**Success Criteria** (what must be TRUE):
  1. `python nixichron_gps.py --self-test` exits 0 and prints "PASS" for all 5 sentences
  2. Each generated sentence begins with `$GPRMC`, ends with `\r\n`, contains exactly 13 comma-separated fields, and status field is always `A`
  3. Checksum is two uppercase hex digits, computed correctly over the bytes between `$` and `*` (exclusive), matching an independent calculator
  4. UTC time field is `hhmmss.00` format sourced from `datetime.now(timezone.utc)` and UTC date field is `ddmmyy` (day-first)
  5. Dummy position, speed, course, and mode fields are present so field offsets are never wrong
**Plans**: 2 plans
Plans:
- [x] 01-01-PLAN.md — Implement nmea_checksum() and build_gprmc() with VAL-03 cross-check checkpoint
- [x] 01-02-PLAN.md — Add verify_gprmc_checksum(), run_self_test(), and --self-test entry point

### Phase 2: CLI Shell and Logging
**Goal**: Users can run the script with `--port`, `--dry-run`, `--self-test`, and `-v` flags and see sentences printed to stdout without touching hardware
**Depends on**: Phase 1
**Requirements**: CLI-01, CLI-02, CLI-03, CLI-04, LOG-01, LOG-02, LOG-03
**Success Criteria** (what must be TRUE):
  1. `python nixichron_gps.py --dry-run` prints valid $GPRMC sentences to stdout with no serial port required
  2. `python nixichron_gps.py --port /dev/cu.usbserial-X` stores the port name for later serial use (no error if port absent in dry-run)
  3. Running with `-v` shows DEBUG-level sentence output; without it, only INFO and above appear
  4. All output uses Python `logging` module — no bare `print()` statements in non-dry-run paths
**Plans**: 2 plans
Plans:
- [x] 02-01-PLAN.md — Write tests/test_cli.py test scaffold (RED): 12 tests for parse_args(), dry-run, and -v logging
- [ ] 02-02-PLAN.md — Add parse_args(), setup_logging(), main() to nixichron_gps.py (GREEN): all 24 tests pass

### Phase 3: Timing Loop
**Goal**: Sentences are emitted at exactly 1 Hz, with the `$` character (the clock's 1 PPS trigger) transmitted as close to the UTC second boundary as possible, without drift accumulating over time
**Depends on**: Phase 2
**Requirements**: TIME-01, TIME-02, TIME-03
**Success Criteria** (what must be TRUE):
  1. Running `--dry-run` for 10 seconds produces exactly 10 sentences with timestamps advancing by 1 second each
  2. Sentence timestamps in dry-run output match the host's UTC second (verifiable with `date -u`)
  3. The loop uses deadline-based sleep (`math.ceil(time.time())`) — not naive `time.sleep(1)` — so execution overhead does not accumulate as drift
**Plans**: TBD

### Phase 4: Signal Handling
**Goal**: The script shuts down cleanly on SIGTERM or SIGINT without leaving the serial port in a locked state
**Depends on**: Phase 3
**Requirements**: SIG-01, SIG-02
**Success Criteria** (what must be TRUE):
  1. Pressing Ctrl-C (SIGINT) causes the main loop to exit cleanly and the script terminates without a traceback
  2. `kill <pid>` (SIGTERM) causes the same clean exit path as Ctrl-C
  3. The serial port is closed in a `finally` block, not inside the signal handler, so the USB adapter is never left locked
**Plans**: TBD

### Phase 5: Serial I/O and Reconnect
**Goal**: The script opens the serial port at 4800 baud/8N1 and sends sentences to the NixiChron clock, recovering automatically from disconnects without crashing
**Depends on**: Phase 4
**Requirements**: SER-01, SER-02, SER-03, SER-04
**Success Criteria** (what must be TRUE):
  1. Running without `--dry-run` opens the configured port at 4800 baud, 8N1, no flow control, and the NixiChron clock displays UTC time
  2. Unplugging and replugging the USB adapter causes the script to retry with exponential backoff (1s, 2s, 4s... capped at 30s), logging WARNING on disconnect and INFO on reconnect
  3. Serial write errors are caught as `SerialException` (broadly) and treated as disconnect events — the script never crashes on I/O errors
**Plans**: TBD

### Phase 6: Deployment Artifacts
**Goal**: A new Linux user can clone the repo, follow the README, and have the daemon running as a systemd service feeding the NixiChron clock within 10 minutes
**Depends on**: Phase 5
**Requirements**: DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06
**Success Criteria** (what must be TRUE):
  1. `pip install -r requirements.txt` succeeds and installs pyserial 3.5 with no other dependencies
  2. `nixichron-gps.service` is a valid systemd unit template with `Restart=on-failure`, depends on `network-online.target` and `time-sync.target`, runs as a non-root user placeholder
  3. README contains an ASCII wiring diagram showing DB9 pin 3 (TX) to mini-DIN pin 5, DB9 pin 5 (GND) to mini-DIN pin 1, with explicit "DO NOT CONNECT" warning for mini-DIN pin 2
  4. README troubleshooting covers: clock not locking (wiring/permissions/dialout group), clock counting from 00:00 (status field or UTC issue), macOS `cu.*` vs `tty.*` device naming
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Sentence Engine | 2/2 | Complete   | 2026-04-10 |
| 2. CLI Shell and Logging | 0/2 | Not started | - |
| 3. Timing Loop | 0/? | Not started | - |
| 4. Signal Handling | 0/? | Not started | - |
| 5. Serial I/O and Reconnect | 0/? | Not started | - |
| 6. Deployment Artifacts | 0/? | Not started | - |
