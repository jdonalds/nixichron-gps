---
phase: 06-deployment-artifacts
verified: 2026-04-09T06:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
human_verification:
  - test: "pip install -r requirements.txt on a fresh Linux system"
    expected: "Only pyserial 3.5 is installed; no additional packages pulled in"
    why_human: "Cannot validate actual pip resolution against PyPI without a clean venv and network access in this environment"
  - test: "End-to-end systemd service installation on Linux"
    expected: "User can clone, edit service file, run systemctl enable --now, and daemon starts feeding clock within 10 minutes"
    why_human: "Requires a Linux host with systemd, dialout group, and physical USB-RS232 adapter"
---

# Phase 6: Deployment Artifacts Verification Report

**Phase Goal:** A new Linux user can clone the repo, follow the README, and have the daemon running as a systemd service feeding the NixiChron clock within 10 minutes
**Verified:** 2026-04-09T06:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                                                        | Status     | Evidence                                                                                      |
| --- | ---------------------------------------------------------------------------------------------------------------------------- | ---------- | --------------------------------------------------------------------------------------------- |
| 1   | pip install -r requirements.txt installs pyserial 3.5 with no other dependencies                                            | ✓ VERIFIED | requirements.txt contains exactly one line: `pyserial==3.5` (1-line file confirmed)          |
| 2   | nixichron-gps.service is a valid systemd unit that restarts on failure and waits for NTP sync before starting                | ✓ VERIFIED | `Restart=on-failure`, `After=network-online.target time-sync.target`, `Requires=...` present |
| 3   | README wiring diagram shows DB9 pin 3 to mini-DIN pin 5, DB9 pin 5 to mini-DIN pin 1, and warns DO NOT CONNECT for pin 2   | ✓ VERIFIED | ASCII diagram and table both present; "DO NOT CONNECT" appears twice in README               |
| 4   | README install steps guide a new Linux user from clone to running daemon, including dialout group membership                 | ✓ VERIFIED | Steps: clone, pip install, dialout group, find device, edit service, systemctl enable --now  |
| 5   | README troubleshooting covers all four silent failure modes                                                                  | ✓ VERIFIED | All four sections: clock not locking, 00:00 display, macOS tty hang, missing cu device       |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact                  | Expected                                      | Status     | Details                                                                            |
| ------------------------- | --------------------------------------------- | ---------- | ---------------------------------------------------------------------------------- |
| `requirements.txt`        | Pinned pyserial==3.5, single line             | ✓ VERIFIED | 1 line, exact content `pyserial==3.5`                                             |
| `nixichron-gps.service`   | Systemd unit template with NTP sync guard     | ✓ VERIFIED | 16 lines; all required directives present; placeholder tokens intact               |
| `README.md`               | User-facing install and wiring guide          | ✓ VERIFIED | 230 lines; ASCII diagram, install steps, systemd guide, 4 troubleshooting sections |

### Key Link Verification

| From                    | To                       | Via                                            | Status     | Details                                                               |
| ----------------------- | ------------------------ | ---------------------------------------------- | ---------- | --------------------------------------------------------------------- |
| `nixichron-gps.service` | `src/nixichron_gps.py`   | ExecStart placeholder `/path/to/src/...`       | ✓ WIRED    | Line 9: `ExecStart=/usr/bin/python3 /path/to/src/nixichron_gps.py`  |
| `README.md`             | `nixichron-gps.service`  | Systemd section references unit file by name   | ✓ WIRED    | Lines 124, 144 in README reference `nixichron-gps.service` directly  |

### Data-Flow Trace (Level 4)

Not applicable — Phase 6 artifacts are static documentation and configuration files (requirements.txt, .service unit, README). No dynamic data rendering.

### Behavioral Spot-Checks

| Behavior                                  | Command                                         | Result                                                                    | Status  |
| ----------------------------------------- | ----------------------------------------------- | ------------------------------------------------------------------------- | ------- |
| --self-test exits 0 with 5 PASS lines     | `python3 src/nixichron_gps.py --self-test`      | 5 lines all ending PASS; checksums 5C, 5D, 5A, 5B, 58 are correct        | ✓ PASS  |
| --dry-run produces valid GPRMC sentences  | `python3 src/nixichron_gps.py --dry-run`        | 4 sentences produced in 3s; all begin `$GPRMC`, status `A`, valid format | ✓ PASS  |
| Full pytest suite passes                  | `python3 -m pytest tests/ -q --tb=short`        | 43 passed in 37.04s                                                       | ✓ PASS  |

### Requirements Coverage

| Requirement | Description                                                                                              | Status      | Evidence                                                                        |
| ----------- | -------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------- |
| DEPLOY-01   | `requirements.txt` containing `pyserial==3.5`                                                           | ✓ SATISFIED | File exists, single line `pyserial==3.5`, confirmed by file read and grep       |
| DEPLOY-02   | `nixichron-gps.service` systemd unit file template with placeholders for user and script path            | ✓ SATISFIED | `YOUR_USERNAME` and `/path/to/src/nixichron_gps.py` placeholders present       |
| DEPLOY-03   | Systemd unit: `Restart=on-failure`, depends on `network-online.target` and `time-sync.target`            | ✓ SATISFIED | All three directives confirmed in service file                                  |
| DEPLOY-04   | README with ASCII wiring diagram with DO NOT CONNECT warning for mini-DIN pin 2                          | ✓ SATISFIED | ASCII diagram and table both include explicit DO NOT CONNECT marking            |
| DEPLOY-05   | README install steps: pip install, copy systemd unit, systemctl enable --now, dialout group              | ✓ SATISFIED | All steps present in numbered Installation and Systemd Service sections        |
| DEPLOY-06   | README troubleshooting: clock not locking, 00:00 display, macOS cu.* vs tty.*, dialout group check      | ✓ SATISFIED | All four failure modes have dedicated headlined sections in Troubleshooting     |

**Note on LOG-02:** REQUIREMENTS.md marks LOG-02 ("Serial errors logged at ERROR level") as unchecked/Pending in the checkbox and traceability table. However, the actual implementation in `src/nixichron_gps.py` (lines 267, 275) does call `logger.error(...)` for both open and write failures. This is a documentation discrepancy only — the code satisfies the requirement. LOG-02 is a Phase 2 requirement (not Phase 6), so it is noted here for completeness but does not affect Phase 6 status.

**Note on ROADMAP.md inconsistency:** ROADMAP.md shows Phase 2 as "Not started" in the progress table, while Phase 2's plans are marked complete (`[x]`) in the phase detail section. The test files (test_cli.py etc.) exist and all 43 tests pass, confirming Phase 2 was completed. The progress table appears to be a stale artifact. This does not affect Phase 6.

### Anti-Patterns Found

| File                     | Line | Pattern                | Severity | Impact                                                                       |
| ------------------------ | ---- | ---------------------- | -------- | ---------------------------------------------------------------------------- |
| `nixichron-gps.service`  | 7    | `YOUR_USERNAME`        | ℹ️ Info   | Intentional placeholder — documented in README; user must substitute before install |
| `nixichron-gps.service`  | 8    | `/path/to/src/...`     | ℹ️ Info   | Intentional placeholder — documented in README with `realpath` command       |

No unintentional anti-patterns detected. The two placeholders are load-bearing design choices explicitly required by DEPLOY-02 and documented in the README's systemd install section.

### Human Verification Required

#### 1. Clean pip install on Linux

**Test:** On a fresh Linux system (or clean venv), run `pip install -r requirements.txt` and verify the installed packages.
**Expected:** Only `pyserial 3.5` installed; no transitive dependencies pulled in.
**Why human:** Cannot validate PyPI dependency resolution against a live registry from this environment.

#### 2. End-to-end 10-minute onboarding

**Test:** On a Linux host with systemd, a USB-RS232 adapter, and the NixiChron clock connected:
1. Clone the repo
2. Run `pip install -r requirements.txt`
3. Add user to dialout group and log back in
4. Find device with `ls /dev/ttyUSB*`
5. Edit `nixichron-gps.service` (replace `YOUR_USERNAME` and `/path/to/src/nixichron_gps.py`)
6. `sudo cp nixichron-gps.service /etc/systemd/system/`
7. `sudo systemctl daemon-reload && sudo systemctl enable --now nixichron-gps`
8. Observe NixiChron clock display

**Expected:** Clock displays accurate UTC time within 10 seconds of service start. Total elapsed time under 10 minutes.
**Why human:** Requires physical hardware (USB adapter, NixiChron clock) and a Linux host with systemd that cannot be simulated in this environment.

### Gaps Summary

No gaps. All five observable truths verified. All six DEPLOY requirements satisfied by confirmed file content. The --self-test spot-check and full 43-test suite both pass, confirming the underlying daemon (Phase 1-5 work) that these deployment artifacts document is correctly implemented.

Two human verification items remain — both require physical hardware and/or a live Linux system and cannot be verified programmatically.

---

_Verified: 2026-04-09T06:00:00Z_
_Verifier: Claude (gsd-verifier)_
