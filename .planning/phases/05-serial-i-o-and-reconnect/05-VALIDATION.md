---
phase: 5
slug: serial-i-o-and-reconnect
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + unittest.mock (mock serial port) |
| **Config file** | tests/ directory |
| **Quick run command** | `python3 -m pytest tests/test_serial.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~40 seconds (includes all prior phase tests) |

---

## Sampling Rate

- **After every task commit:** Run `python3 src/nixichron_gps.py --self-test`
- **After every plan wave:** Run full test suite
- **Before `/gsd:verify-work`:** Full suite green + manual hardware test if available
- **Max feedback latency:** 40 seconds

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| NixiChron displays UTC time | SER-01 | Requires physical hardware | Connect USB-RS232 adapter, run without --dry-run, verify clock displays current UTC |
| USB unplug/replug recovery | SER-03 | Requires physical USB disconnect | Unplug adapter while running, verify WARNING log, replug, verify INFO log and resume |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Feedback latency < 40s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
