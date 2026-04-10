# Phase 6: Deployment Artifacts - Research

**Researched:** 2026-04-09
**Domain:** Python deployment packaging — requirements.txt, systemd unit file, README documentation
**Confidence:** HIGH

## Summary

Phase 6 delivers three file types: a `requirements.txt`, a `nixichron-gps.service` systemd unit template, and a `README.md`. None of these require new Python code — the implementation script is complete from Phases 1-5. The work is documentation and configuration authorship.

The entire external dependency surface of the project is one package: `pyserial==3.5`. This is already verified installed on the development machine (confirmed by `pip3 show pyserial`). The systemd unit must declare two `After=` / `Requires=` dependencies (`network-online.target` and `time-sync.target`) and `Restart=on-failure` so the daemon recovers from port disconnects that slip past the backoff logic. The README must convey wiring, install, and troubleshooting with enough specificity that a new Linux user reaches a running daemon in under 10 minutes without requiring a response from the author.

The highest-risk element of this phase is documentation accuracy. Wrong wiring instructions can damage hardware (mini-DIN pin 2 is +5V — a short here could destroy the clock's power rail). Wrong device names on macOS (`tty.*` instead of `cu.*`) cause a hung process with no error message. Both are silent failures from the user's perspective. Research priority is therefore correctness of specific technical details, not library selection.

**Primary recommendation:** Author all three files in a single plan. There is no code to TDD, so the Red/Green split used in prior phases does not apply. Write the files, verify each against the requirements checklist, and mark complete.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPLOY-01 | `requirements.txt` containing `pyserial==3.5` | pyserial 3.5 confirmed installed and the sole external dependency; no other packages used |
| DEPLOY-02 | `nixichron-gps.service` systemd unit template with placeholders for user and script path | Systemd unit syntax documented below; placeholder conventions established |
| DEPLOY-03 | Systemd unit: `Restart=on-failure`, depends on `network-online.target` and `time-sync.target`, runs as non-root user | Standard systemd service hardening patterns; `time-sync.target` ensures NTP lock before daemon starts |
| DEPLOY-04 | `README.md` ASCII wiring diagram: DB9 pin 3 TX to mini-DIN 5, DB9 pin 5 GND to mini-DIN 1, mini-DIN 2 DO NOT CONNECT, mini-DIN 4 floating | Wiring locked in PROJECT.md; ASCII art pattern shown below |
| DEPLOY-05 | README install steps: `pip install -r requirements.txt`, copy systemd unit, `systemctl enable --now` | Standard Linux install sequence with dialout group membership prerequisite |
| DEPLOY-06 | README troubleshooting: clock not locking, clock counting from 00:00, NMEA verify with cat loopback, macOS cu.* vs tty.* | All troubleshooting scenarios researched and verified against project pitfalls |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary — this phase requires exactly three new files: `requirements.txt`, `nixichron-gps.service`, `README.md`
- NEVER save to root folder — `requirements.txt` and the systemd unit live at repo root by convention (this is standard for Python projects; the CLAUDE.md rule targets working files, not shipped artifacts); README.md also lives at repo root
- ALWAYS read a file before editing it
- Keep files under 500 lines
- No GUI, no web interface, no NTP library (already out of scope)
- Python 3.9+ only (no match/case, no X | Y union types)

## Standard Stack

### Core
| File | Purpose | Standard? |
|------|---------|-----------|
| `requirements.txt` | pip dependency manifest | Universal Python convention |
| `nixichron-gps.service` | systemd service unit | Standard Linux daemon deployment |
| `README.md` | User-facing documentation | Universal open source convention |

### Dependencies
| Package | Version | Why Pinned |
|---------|---------|------------|
| pyserial | 3.5 | Only external dependency; pinned for reproducibility; confirmed current (verified 2026-04-09 via pip3 show) |

**Installation verification:**
```bash
pip3 show pyserial
# Name: pyserial
# Version: 3.5
```

pyserial 3.5 is confirmed installed and matches the pinned version. No version upgrade needed.

## Architecture Patterns

### File Layout
```
newnixie/           (repo root)
├── requirements.txt            # DEPLOY-01
├── nixichron-gps.service       # DEPLOY-02, DEPLOY-03
├── README.md                   # DEPLOY-04, DEPLOY-05, DEPLOY-06
└── src/
    └── nixichron_gps.py        # Existing — not modified in Phase 6
```

Note: `requirements.txt` and `nixichron-gps.service` live at repo root. This is standard Python project layout. The CLAUDE.md prohibition on saving to root targets temporary working files, not shipped project artifacts.

### Pattern 1: requirements.txt
**What:** Single-line pinned dependency file
**When to use:** Always for Python projects with external dependencies

```
pyserial==3.5
```

No `>=`, no unpinned, no transitive deps listed (pyserial has none). Exact pin (`==`) ensures reproducibility across installs.

### Pattern 2: Systemd Service Unit Template
**What:** A `.service` file with placeholder tokens the user replaces before installing
**When to use:** When the install path and user are deployment-specific

Canonical systemd unit structure for a Python daemon:

```ini
[Unit]
Description=NixiChron GPS Emulator — feeds $GPRMC sentences to the Nixie clock
After=network-online.target time-sync.target
Requires=network-online.target time-sync.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/bin/python3 /path/to/src/nixichron_gps.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Placeholder conventions:**
- `YOUR_USERNAME` — replaced by actual Linux username
- `/path/to/src/nixichron_gps.py` — replaced by absolute path after clone

**Why `time-sync.target`:** The daemon reads UTC from the system clock. If NTP has not synced when the daemon starts (common on boot), the clock will display wrong time until the host clock corrects. `Requires=time-sync.target` blocks daemon start until chrony/systemd-timesyncd confirms sync. This is the correct dependency for any time-sensitive daemon.

**Why `network-online.target`:** Required by `time-sync.target` transitively; declaring it explicitly makes the dependency clear in the unit file.

**Why `Restart=on-failure`:** The daemon has its own exponential backoff reconnect for serial disconnects, but a crash (unexpected exception) would stop the daemon permanently. `Restart=on-failure` provides a systemd-level safety net. `RestartSec=5` prevents tight restart loops.

**Why `Type=simple`:** The process does not fork; it runs directly. `simple` is the correct type for Python scripts that do not daemonize themselves.

### Pattern 3: ASCII Wiring Diagram

Standard ASCII art for DB9 to mini-DIN serial wiring:

```
  DB9 Female             6-Pin Mini-DIN
  (USB adapter)          (NixiChron GPS port)
  ___________            ___________
 |           |          |           |
 | Pin 3 TX  |--------->| Pin 5 RX  |  (data)
 | Pin 5 GND |--------->| Pin 1 GND |  (ground)
 |           |          |           |
 |           |          | Pin 2     |  DO NOT CONNECT (+5V rail)
 |           |          | Pin 4     |  Leave floating
 |___________|          |___________|
```

The "DO NOT CONNECT" warning for pin 2 is safety-critical — it carries the clock's +5V supply rail. Connecting it to the DB9 adapter could damage hardware.

### Pattern 4: README Structure for 10-Minute Install Goal

Section order optimized for "clone → running in 10 minutes":

1. **What This Is** (2-3 lines) — what it does and why
2. **Requirements** — hardware, OS, Python version
3. **Hardware Wiring** — ASCII diagram + pin table with DO NOT CONNECT warnings
4. **Installation** — numbered steps, copy-pasteable commands
5. **Running** — quick start (dry-run first, then live)
6. **Systemd Service** — how to install and enable
7. **Troubleshooting** — categorized by symptom

### Anti-Patterns to Avoid

- **Vague placeholders:** "edit the config" without specifying what to replace. Use explicit `YOUR_USERNAME` tokens with inline comments explaining what to replace.
- **Missing `dialout` group step:** Omitting `sudo usermod -aG dialout $USER` in install steps means the user hits a permissions error at first run with no obvious explanation.
- **macOS-only device paths in Linux docs:** The README serves both platforms. Use conditional sections or clear platform labels.
- **Relative paths in systemd ExecStart:** Systemd does not inherit the user's `$PATH` in the same way. `ExecStart` should use the absolute path to `python3` (found via `which python3`) and the absolute path to the script.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Dependency management | Custom install script | `pip install -r requirements.txt` | Standard; works with virtualenvs, pip-tools, pipx |
| Daemon supervision | Custom watchdog loop in Python | systemd `Restart=on-failure` | OS-managed; survives script crashes, not just SerialException |
| Service startup ordering | Manual sleep before serial open | systemd `After=time-sync.target` | Declarative; correct even after system suspend/resume |

**Key insight:** The daemon has application-level reconnect (exponential backoff), but the systemd unit provides infrastructure-level supervision. Both layers are needed and neither replaces the other.

## Common Pitfalls

### Pitfall 1: mini-DIN Pin 2 Wiring Error
**What goes wrong:** User connects DB9 to mini-DIN pin 2, creating a short between the adapter's TX line and the clock's +5V supply rail.
**Why it happens:** Six-pin mini-DIN diagrams vary by standard; pin 2 is the most likely "next pin" a user tries after pin 1.
**How to avoid:** README must state "DO NOT CONNECT" in capital letters for pin 2, with a parenthetical explaining it carries +5V. The ASCII diagram should show it with explicit warning text, not just leave it blank.
**Warning signs:** Clock stops working after first wiring attempt; USB adapter no longer recognized.

### Pitfall 2: dialout Group Not Set
**What goes wrong:** `python3 src/nixichron_gps.py --port /dev/ttyUSB0` fails with `[Errno 13] Permission denied`.
**Why it happens:** On Linux, `/dev/ttyUSB*` is owned by the `dialout` group. A fresh user account is not in this group.
**How to avoid:** Install steps must include `sudo usermod -aG dialout $USER` followed by a log-out-and-back-in instruction. This must come before the first `python3` command.
**Warning signs:** `ls -la /dev/ttyUSB0` shows `crw-rw---- 1 root dialout`; `groups` does not include `dialout`.

### Pitfall 3: macOS tty.* Device Hangs on Open
**What goes wrong:** User runs `python3 src/nixichron_gps.py --port /dev/tty.usbserial-XXXX` and the script hangs with no output.
**Why it happens:** macOS `tty.*` devices are dial-in and block `open()` until DCD is asserted. The NixiChron never asserts DCD.
**How to avoid:** README must explicitly state: "On macOS, always use `cu.*` not `tty.*`." Include the `ls /dev/cu.*` discovery command. Flag this in the troubleshooting section under "script hangs at startup."
**Warning signs:** No output, no error, process visible in `ps aux` but nothing happening.

### Pitfall 4: macOS Sequoia Driver Approval Required
**What goes wrong:** No `/dev/cu.*` device appears after plugging in a CH340 or Prolific USB-serial adapter.
**Why it happens:** macOS Sequoia (15+) requires driver extension approval in System Settings > Privacy & Security. CH340/Prolific vendors may not have shipped a dext version.
**How to avoid:** Troubleshooting section must include: (1) check `ls /dev/cu.*`, (2) check Privacy & Security for blocked extension, (3) recommend FTDI chipset as the reliable alternative (Apple ships a native FTDI dext).
**Warning signs:** `ls /dev/cu.*` returns nothing after plugging in adapter.

### Pitfall 5: Clock Counting from 00:00 (Not Locking)
**What goes wrong:** NixiChron displays time but counts from 00:00:00 or an arbitrary start, ignoring the NMEA sentences.
**Why it happens:** Two possible root causes — (a) status field is `V` instead of `A`, or (b) time field contains local time instead of UTC.
**How to avoid:** Troubleshooting section must cover both sub-causes. Diagnostic command: `python3 src/nixichron_gps.py --dry-run | head -3` — inspect field 2 (must be `A`) and compare timestamp to `date -u`.
**Warning signs:** Clock counts upward from 00:00 regardless of system time, or displays time that is offset by the local UTC offset.

### Pitfall 6: Clock Not Locking at All (No Display Update)
**What goes wrong:** NixiChron does not change its display after connection.
**Why it happens:** Multiple possible causes: TX/GND wires swapped or disconnected, wrong baud rate (but this is fixed in code at 4800), serial port permissions, or the adapter is not actually transmitting.
**How to avoid:** Troubleshooting must provide a diagnostic sequence: (1) verify wiring with multimeter, (2) verify device exists with `ls /dev/ttyUSB0`, (3) verify permissions with `ls -la /dev/ttyUSB0`, (4) verify TX output with `cat /dev/ttyUSB0` (loopback test — connect TX to RX on the adapter and run `--dry-run`).
**Warning signs:** No change in clock display after 10+ seconds of running the script.

### Pitfall 7: Systemd Unit Fails to Start — Path Issues
**What goes wrong:** `systemctl start nixichron-gps` fails with `ExecStart= not found` or `No such file or directory`.
**Why it happens:** User copied the unit file with placeholder paths (`/path/to/...`) without substituting actual values.
**How to avoid:** Install steps must explicitly say "open the service file and replace `YOUR_USERNAME` and `/path/to/src/nixichron_gps.py` with your actual values." Provide the `which python3` command to find the Python path. Provide `pwd` or `realpath` to find the script path.
**Warning signs:** `systemctl status nixichron-gps` shows `code=exited, status=203/EXEC`.

## Code Examples

### requirements.txt (complete file)
```
# Source: pyserial official docs — https://pyserial.readthedocs.io/en/latest/
pyserial==3.5
```

### nixichron-gps.service (complete template)
```ini
# Source: systemd.service(5) man page — https://www.freedesktop.org/software/systemd/man/systemd.service.html
# NixiChron GPS Emulator systemd service unit
# INSTALL:
#   1. Edit: replace YOUR_USERNAME and /path/to/src/nixichron_gps.py
#   2. sudo cp nixichron-gps.service /etc/systemd/system/
#   3. sudo systemctl daemon-reload
#   4. sudo systemctl enable --now nixichron-gps

[Unit]
Description=NixiChron GPS Emulator — feeds $GPRMC sentences to the Nixie clock
After=network-online.target time-sync.target
Requires=network-online.target time-sync.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/bin/python3 /path/to/src/nixichron_gps.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### README Wiring Section (ASCII diagram + pin table)
```markdown
## Hardware Wiring

Connect a USB-to-RS232 adapter (DB9 female) to the NixiChron's 6-pin mini-DIN GPS port:

```
  DB9 Female (USB adapter)         6-Pin Mini-DIN (NixiChron GPS port)
  ┌─────────────────────┐          ┌──────────────────────────────────┐
  │ Pin 3  TX (transmit)│─────────►│ Pin 5  RX (clock receive)        │
  │ Pin 5  GND (ground) │─────────►│ Pin 1  GND (ground)              │
  │                     │          │ Pin 2  DO NOT CONNECT (+5V rail!) │
  │                     │          │ Pin 4  Leave floating             │
  └─────────────────────┘          └──────────────────────────────────┘
```

| DB9 Pin | Signal | Mini-DIN Pin | Action           |
|---------|--------|--------------|------------------|
| 3       | TX     | 5            | Connect          |
| 5       | GND    | 1            | Connect          |
| —       | —      | 2            | DO NOT CONNECT   |
| —       | —      | 4            | Leave floating   |

**WARNING: Mini-DIN pin 2 carries the clock's +5V power rail. Connecting it to the DB9 adapter will damage hardware.**
```

### README Troubleshooting Scenarios
```markdown
## Troubleshooting

### Clock not locking (display unchanged after 10+ seconds)

1. **Check wiring:** Confirm DB9 pin 3 → mini-DIN pin 5 and DB9 pin 5 → mini-DIN pin 1.
   Use a multimeter to verify continuity.
2. **Check device exists:** `ls /dev/ttyUSB0` (Linux) or `ls /dev/cu.*` (macOS).
   If missing, the adapter is not recognized — check driver installation.
3. **Check permissions (Linux):** `ls -la /dev/ttyUSB0`
   If you see `crw-rw---- 1 root dialout`, you need dialout group membership:
   `sudo usermod -aG dialout $USER` then log out and back in.
4. **Verify TX output (loopback test):** Connect DB9 pin 3 to pin 2 (TX to RX loopback),
   then run `python3 src/nixichron_gps.py --dry-run` in one terminal and
   `cat /dev/ttyUSB0` (Linux) or `cat /dev/cu.usbserial-XXXX` (macOS) in another.
   You should see NMEA sentences appear in the second terminal.

### Clock counting from 00:00 (not using system time)

1. **Verify status field is A:** Run `python3 src/nixichron_gps.py --dry-run | head -3`
   Field 2 in each sentence must be `A`, not `V`.
   Example: `$GPRMC,123456.00,**A**,0000.0000,...`
2. **Verify UTC time:** Compare the timestamp in `--dry-run` output to `date -u`.
   They must match within 1 second. If offset by hours, the host clock timezone is wrong.

### Script hangs at startup (no output, no error) — macOS only

You are using a `tty.*` device. On macOS, always use `cu.*`:
- Wrong: `/dev/tty.usbserial-XXXX`
- Correct: `/dev/cu.usbserial-XXXX`

List available devices: `ls /dev/cu.*`

### No /dev/cu.* device after plugging in adapter — macOS only

Your adapter requires a third-party driver that macOS has blocked.
1. Open **System Settings > Privacy & Security** and look for a blocked driver extension.
   Click **Allow** and restart your Mac.
2. If no blocked extension appears, your adapter's chipset (CH340/Prolific) may not have
   a driver compatible with your macOS version.
   **Recommendation:** Use an FTDI-chipset adapter — macOS includes native FTDI support.
```

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `EnvironmentFile=` for secrets in systemd units | `Environment=` inline or `EnvironmentFile=` pointing to `/etc/default/nixichron-gps` | Not needed here — only `GPS_PORT` env var, which defaults safely |
| `Type=forking` for Python daemons | `Type=simple` | Python scripts do not fork; `simple` is correct |
| `WantedBy=default.target` | `WantedBy=multi-user.target` | `multi-user.target` is correct for network-dependent daemons |

**Deprecated / avoid:**
- `After=network.target` alone (without `network-online.target`): `network.target` means interfaces are up, not that they have addresses. For NTP sync, `network-online.target` is required.
- `datetime.utcnow()`: Removed from Python 3.12 deprecation path — already avoided in this codebase; worth noting in README if users see it in examples online.

## Open Questions

1. **Should `GPS_PORT` env var support be documented in README?**
   - What we know: `parse_args()` reads `os.environ.get('GPS_PORT', '/dev/ttyUSB0')` — this is already implemented.
   - What's unclear: Whether to expose this in README install steps or only in the systemd unit via `Environment=GPS_PORT=...`.
   - Recommendation: Document the env var in the systemd section as an alternative to `--port` in `ExecStart`. Planner decides.

2. **README placement of macOS sections**
   - What we know: PROJECT.md lists macOS as the primary host OS; Linux is secondary.
   - What's unclear: Should macOS-specific steps appear first or in a separate section?
   - Recommendation: Use platform labels (`**Linux:**`, `**macOS:**`) inline rather than separate sections, to keep install steps scannable as a single list.

3. **Should `requirements.txt` include a comment line?**
   - What we know: pip supports `#` comments in requirements.txt.
   - What's unclear: Whether a comment adds value or noise.
   - Recommendation: One comment line pointing to pyserial docs. Planner decides.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python 3.9+ | All deployment steps | Yes | 3.9.6 | — |
| pyserial | `requirements.txt` install test | Yes (dev machine) | 3.5 | — |
| systemd | `nixichron-gps.service` | No (macOS dev machine) | — | Not needed — unit file is text; no systemd commands run in this phase |
| pip3 | Install step verification | Yes | bundled with Python 3.9.6 | — |

**Missing dependencies with no fallback:**
- None that block Phase 6 execution. systemd is not available on the macOS dev machine, but Phase 6 only creates the unit file — it does not install or start it.

**Missing dependencies with fallback:**
- systemd (absent on macOS): The unit file is plain text authored by this phase. Syntax validation could be done by running `systemd-analyze verify nixichron-gps.service` on a Linux host, but this is not required for Phase 6 completion. The planner should add a note that the unit file syntax was not machine-validated.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (detected — `.pytest_cache/` present, test files use pytest patterns) |
| Config file | none — inferred from directory structure |
| Quick run command | `python3 -m pytest tests/ -x -q` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEPLOY-01 | `requirements.txt` contains `pyserial==3.5` | smoke | `python3 -c "open('requirements.txt').read()" && grep 'pyserial==3.5' requirements.txt` | No — file created in this phase |
| DEPLOY-02 | `nixichron-gps.service` exists and contains placeholder tokens | smoke | `grep 'YOUR_USERNAME' nixichron-gps.service && grep 'Restart=on-failure' nixichron-gps.service` | No — file created in this phase |
| DEPLOY-03 | Systemd unit has correct `After=` / `Requires=` and `Restart=` directives | smoke | `grep 'time-sync.target' nixichron-gps.service && grep 'network-online.target' nixichron-gps.service` | No — file created in this phase |
| DEPLOY-04 | README contains ASCII wiring diagram with correct pin references | smoke | `grep 'Pin 3' README.md && grep 'Pin 5' README.md && grep 'DO NOT CONNECT' README.md` | No — file created in this phase |
| DEPLOY-05 | README install steps include pip install and systemctl commands | smoke | `grep 'pip install' README.md && grep 'systemctl enable' README.md && grep 'dialout' README.md` | No — file created in this phase |
| DEPLOY-06 | README troubleshooting covers cu.* vs tty.*, dialout group, and counting from 00:00 | smoke | `grep 'cu\.' README.md && grep 'dialout' README.md && grep '00:00' README.md` | No — file created in this phase |

### Sampling Rate
- **Per task commit:** Run smoke checks above (grep-based, < 5 seconds each)
- **Per wave merge:** Full pytest suite to confirm no regressions in Phases 1-5
- **Phase gate:** All smoke checks green + full suite green before marking Phase 6 complete

### Wave 0 Gaps
- All three files (`requirements.txt`, `nixichron-gps.service`, `README.md`) are authored in this phase — no pre-existing test infrastructure covers them.
- No new pytest tests are needed for Phase 6 (these are static files, not Python code). Smoke validation via grep is sufficient and faster.
- Existing test suite (`tests/test_cli.py`, `tests/test_serial.py`, `tests/test_signal.py`, `tests/test_timing.py`, `tests/test_verify_and_self_test.py`) must remain green — run after creating files to confirm nothing was accidentally broken.

## Sources

### Primary (HIGH confidence)
- systemd.service(5) man page — https://www.freedesktop.org/software/systemd/man/systemd.service.html — `Restart=on-failure`, `Type=simple`, `After=` / `Requires=` ordering
- systemd.special(7) — https://www.freedesktop.org/software/systemd/man/systemd.special.html — `time-sync.target` and `network-online.target` semantics
- pyserial official docs — https://pyserial.readthedocs.io/en/latest/ — confirmed version 3.5 is the current stable release
- Project PITFALLS.md — Pitfalls 7 (tty.* vs cu.*) and 8 (macOS driver approval) — HIGH confidence, already verified against primary sources in Phase 1 research
- Project PROJECT.md — Wiring table (DB9 pin 3 → mini-DIN pin 5, DB9 pin 5 → mini-DIN pin 1) — authoritative for this project
- Project STATE.md — Confirmed Phases 1-5 complete; pyserial==3.5 the sole dependency

### Secondary (MEDIUM confidence)
- pip requirements.txt format specification — https://pip.pypa.io/en/stable/reference/requirements-file-format/ — exact-pin `==` syntax
- macOS cu.* vs tty.* blocking behavior — https://www.codegenes.net/blog/what-s-the-difference-between-dev-tty-and-dev-cu-on-macos/ — verified against Project PITFALLS.md Pitfall 7
- macOS USB serial driver approval — https://www.mac-usb-serial.com/docs/support/troubleshooting.html — verified against Project PITFALLS.md Pitfall 8

### Tertiary (LOW confidence / needs hardware validation)
- NixiChron response time to first valid sentence — how many sentences before display updates is not documented publicly; estimated 1-3 seconds based on GPS clock conventions

## Metadata

**Confidence breakdown:**
- requirements.txt content: HIGH — single known dependency, version confirmed installed
- systemd unit structure: HIGH — standard systemd patterns, well-documented
- README wiring details: HIGH — locked in PROJECT.md, sourced from hardware documentation
- macOS troubleshooting: HIGH — verified in project PITFALLS.md against primary sources
- Clock lock behavior specifics: MEDIUM — inferred from NMEA standard, not confirmed against NixiChron firmware

**Research date:** 2026-04-09
**Valid until:** 2026-05-09 (stable domain — systemd and pip formats do not change rapidly)
