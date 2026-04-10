---
phase: 2
slug: cli-shell-and-logging
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing from Phase 1) + manual CLI verification |
| **Config file** | tests/ directory |
| **Quick run command** | `python3 src/nixichron_gps.py --self-test && python3 src/nixichron_gps.py --dry-run 2>/dev/null \| head -3` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~15 seconds (5 subprocess tests × 3s timeout each; normal) |

---

## Sampling Rate

- **After every task commit:** Run `python3 src/nixichron_gps.py --self-test`
- **After every plan wave:** Run full test suite + dry-run visual check
- **Before `/gsd:verify-work`:** Full suite must be green + dry-run produces valid sentences
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | CLI-01,02,03,04 | integration | `python3 src/nixichron_gps.py --self-test` | ✅ | ⬜ pending |
| 02-01-02 | 01 | 1 | LOG-01,02,03 | integration | `python3 -m pytest tests/ -q` | ✅ | ⬜ pending |
| 02-01-03 | 01 | 1 | VAL-02 | manual | `python3 src/nixichron_gps.py --dry-run \| head -5` | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing test infrastructure from Phase 1 covers base requirements.

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| --dry-run output is valid NMEA | VAL-02 | Visual inspection of sentence format | Run `python3 src/nixichron_gps.py --dry-run` for 5s, verify $GPRMC format and current UTC time |
| -v flag shows DEBUG output | CLI-04 | Log level visual check | Run with and without -v, compare output verbosity |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
