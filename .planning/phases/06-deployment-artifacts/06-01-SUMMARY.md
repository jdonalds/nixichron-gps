---
phase: 06-deployment-artifacts
plan: 01
subsystem: infra
tags: [pyserial, systemd, rs232, nmea, nixichron, deployment]

# Dependency graph
requires:
  - phase: 05-serial-i-o-and-reconnect
    provides: nixichron_gps.py with parse_args, open_serial, GPS_PORT env var support
provides:
  - requirements.txt with pinned pyserial==3.5 dependency
  - nixichron-gps.service systemd unit template with NTP sync guard
  - README.md with ASCII wiring diagram, install steps, and troubleshooting guide
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Systemd unit with time-sync.target dependency ensures NTP lock before daemon starts"
    - "Placeholder tokens (YOUR_USERNAME, /path/to/src/nixichron_gps.py) for user substitution before deploy"

key-files:
  created:
    - requirements.txt
    - nixichron-gps.service
    - README.md
  modified: []

key-decisions:
  - "requirements.txt uses exact pin (==) not range — pyserial 3.5 has no transitive deps so single line is correct"
  - "Systemd unit depends on time-sync.target to prevent clock displaying wrong time on boot after NTP sync"
  - "README covers all four silent failure modes identified in research: clock not locking, 00:00 display, macOS tty hang, missing cu device"

patterns-established:
  - "Wiring diagram: DB9 pin 3 (TX) -> mini-DIN pin 5 (RX), DB9 pin 5 (GND) -> mini-DIN pin 1 (GND)"
  - "mini-DIN pin 2 is +5V power rail — explicit DO NOT CONNECT warning required"

requirements-completed: [DEPLOY-01, DEPLOY-02, DEPLOY-03, DEPLOY-04, DEPLOY-05, DEPLOY-06]

# Metrics
duration: 2min
completed: 2026-04-10
---

# Phase 06 Plan 01: Deployment Artifacts Summary

**requirements.txt pinned to pyserial==3.5, systemd unit guarded by time-sync.target, and README with ASCII wiring diagram covering all four NixiChron silent failure modes**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-10T05:19:30Z
- **Completed:** 2026-04-10T05:21:33Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- requirements.txt with single pinned line `pyserial==3.5` — reproducible installs, no transitive deps
- nixichron-gps.service systemd unit template that blocks on NTP sync (time-sync.target) before starting
- README with complete ASCII wiring diagram (DB9 to mini-DIN), dialout group setup, systemd install, and four troubleshooting sections

## Task Commits

Each task was committed atomically:

1. **Task 1: Write requirements.txt** - `5935a9e` (chore)
2. **Task 2: Write nixichron-gps.service systemd unit template** - `421ac97` (chore)
3. **Task 3: Write README.md** - `d36fdb5` (docs)

## Files Created/Modified

- `requirements.txt` - Pinned pyserial==3.5 dependency manifest
- `nixichron-gps.service` - Systemd unit template with NTP sync guard, Restart=on-failure, and user/path placeholders
- `README.md` - ASCII wiring diagram, Linux/macOS install steps, systemd service guide, four troubleshooting sections

## Decisions Made

- Used exact pin (==) not range (~=) in requirements.txt — pyserial 3.5 is the latest stable and has no transitive dependencies, so a single line is correct
- Systemd unit depends on `time-sync.target` to prevent the clock from displaying wrong time on boot before NTP sync completes
- README troubleshooting covers all four silent failure modes from RESEARCH.md: clock not locking, clock at 00:00, macOS tty.* hang, and missing cu.* device

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all three files were written as specified. Full test suite (43 tests) passed with no regressions.

## User Setup Required

Users must edit `nixichron-gps.service` before installing:
- Replace `YOUR_USERNAME` with their Linux username (`whoami`)
- Replace `/path/to/src/nixichron_gps.py` with the absolute path (`realpath src/nixichron_gps.py`)

See README.md Systemd Service section for full instructions.

## Next Phase Readiness

Phase 6 is the final phase. The project is complete:
- All NMEA sentence generation, timing, logging, signal handling, and serial I/O is implemented in `src/nixichron_gps.py`
- Deployment artifacts are in place: `requirements.txt`, `nixichron-gps.service`, `README.md`
- 43 tests passing with full coverage of core logic

---
*Phase: 06-deployment-artifacts*
*Completed: 2026-04-10*
