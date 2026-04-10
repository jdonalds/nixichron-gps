---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: verifying
stopped_at: Completed 06-deployment-artifacts/06-01-PLAN.md
last_updated: "2026-04-10T05:22:20.619Z"
last_activity: 2026-04-10
progress:
  total_phases: 6
  completed_phases: 6
  total_plans: 10
  completed_plans: 10
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-09)

**Core value:** The NixiChron clock displays accurate UTC time from the host's NTP-synced system clock, without a real GPS module.
**Current focus:** Phase 06 — deployment-artifacts

## Current Position

Phase: 06 (deployment-artifacts) — EXECUTING
Plan: 1 of 1
Status: Phase complete — ready for verification
Last activity: 2026-04-10

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 5
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 03 | 1 | - | - |
| 04 | 2 | - | - |
| 05 | 2 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion*
| Phase 01-core-sentence-engine P01 | 2 | 2 tasks | 1 files |
| Phase 01-core-sentence-engine P02 | 15 | 2 tasks | 2 files |
| Phase 02-cli-shell-and-logging P01 | 1 | 1 tasks | 1 files |
| Phase 02-cli-shell-and-logging P02 | 8 | 2 tasks | 1 files |
| Phase 03-timing-loop P01 | 35 | 2 tasks | 2 files |
| Phase 04-signal-handling P01 | 1 | 1 tasks | 1 files |
| Phase 04-signal-handling P02 | 8 | 1 tasks | 1 files |
| Phase 05-serial-i-o-and-reconnect P01 | 5 | 1 tasks | 1 files |
| Phase 05 P02 | 8 | 2 tasks | 1 files |
| Phase 06-deployment-artifacts P01 | 2 | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Use OS clock only (`datetime.now(timezone.utc)`) — no ntplib
- Single flat script `nixichron_gps.py` — no package structure
- 4800 baud fixed — not configurable; NixiChron requires it exactly
- Phases 1-4 are hardware-free; Phase 5 is the first requiring physical serial port
- [Phase 01-core-sentence-engine]: nmea_checksum receives full dollar-sign-body-star string so the [1:index(*)] slice is always correct whether called from builder or verifier
- [Phase 01-core-sentence-engine]: build_gprmc is a pure function — caller captures datetime.now(timezone.utc) and passes it in (D-05)
- [Phase 01-core-sentence-engine]: Verified checksum for datetime(2026,4,9,12,34,56,utc) is 50 (0x50 = 80 decimal) — VAL-03 satisfied
- [Phase 01-core-sentence-engine]: verify_gprmc_checksum is a fully independent XOR loop — does not call nmea_checksum() (D-02), catching off-by-one bugs
- [Phase 01-core-sentence-engine]: run_self_test uses fixed base datetime(2026,1,15,12,0,0,utc) with 1-hour increments so all 5 sentences have distinct time digits
- [Phase 02-cli-shell-and-logging]: importlib.util.spec_from_file_location used for module loading to avoid sys.path pollution across tests
- [Phase 02-cli-shell-and-logging]: subprocess.Popen + communicate(timeout=3) + SIGTERM chosen for testing infinite-loop --dry-run scripts
- [Phase 02-cli-shell-and-logging]: parse_args(args=None) pattern enables unit tests to inject arg lists without touching sys.argv
- [Phase 02-cli-shell-and-logging]: setup_logging called from main() after parse_args — logging.basicConfig is one-shot, must know verbose flag first
- [Phase 02-cli-shell-and-logging]: sys.stdout.buffer.write (binary) preserves exact CRLF bytes required by NixiChron firmware
- [Phase 03-timing-loop]: sleep_until_next_second() uses math.ceil(time.time()) deadline approach — self-correcting per iteration, no drift accumulation
- [Phase 03-timing-loop]: main() loop order: sleep_until_next_second() called first, datetime.now(timezone.utc) immediately after — timestamp reflects post-boundary wall time
- [Phase 03-timing-loop]: _load_module() registers module in sys.modules['nixichron_gps'] so unittest.mock.patch can resolve patching targets by module name
- [Phase 04-signal-handling]: Signal test start detection uses proc.stdout.read(64) loop with 5s deadline — avoids flaky fixed sleep
- [Phase 04-signal-handling]: Source inspection uses SRC_PATH.read_text() not _load_module() for structural assertion tests
- [Phase 04-signal-handling]: Signal handlers registered inside main() after self-test check so --self-test mode runs unaffected by SIGTERM/SIGINT registration
- [Phase 04-signal-handling]: port = None before try block ensures finally clause is safe when Phase 5 has not yet assigned a real port object
- [Phase 05-serial-i-o-and-reconnect]: patch parse_args (return_value=Namespace) rather than sys.argv — cleaner isolation of main() in serial tests
- [Phase 05-serial-i-o-and-reconnect]: mod._shutdown = True inside fake_open_serial side_effect — deterministic loop-break without threading
- [Phase 05-serial-i-o-and-reconnect]: Backoff state persists before outer while loop — re-defining inside else block reset delay on every tick
- [Phase 05-serial-i-o-and-reconnect]: time.sleep(_BACKOFF_BASE) added after write failure so reconnect phase shows reset-to-1.0 sleep even when reconnect succeeds immediately
- [Phase 05-serial-i-o-and-reconnect]: port = None set after delay sleep and before port.close() to prevent double-close on exception
- [Phase 06-deployment-artifacts]: requirements.txt uses exact pin (==) — pyserial 3.5 has no transitive deps, single line is correct
- [Phase 06-deployment-artifacts]: Systemd unit depends on time-sync.target to prevent clock displaying wrong time before NTP sync on boot
- [Phase 06-deployment-artifacts]: README troubleshooting covers all four silent failure modes: clock not locking, 00:00 display, macOS tty hang, missing cu device

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 5 (serial I/O): NixiChron firmware lock behavior not confirmed against actual hardware — validate empirically
- Phase 5: macOS Sequoia driver compatibility for CH340/Prolific adapters is uncertain; recommend FTDI chipset

## Session Continuity

Last session: 2026-04-10T05:22:20.616Z
Stopped at: Completed 06-deployment-artifacts/06-01-PLAN.md
Resume file: None
