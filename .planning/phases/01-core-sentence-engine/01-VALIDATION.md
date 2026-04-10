---
phase: 1
slug: core-sentence-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-09
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Built-in `--self-test` flag (no external test framework needed) |
| **Config file** | none — self-test is built into the script |
| **Quick run command** | `python src/nixichron_gps.py --self-test` |
| **Full suite command** | `python src/nixichron_gps.py --self-test` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `python src/nixichron_gps.py --self-test`
- **After every plan wave:** Run `python src/nixichron_gps.py --self-test`
- **Before `/gsd:verify-work`:** Self-test must exit 0
- **Max feedback latency:** 1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | NMEA-02 | unit | `python src/nixichron_gps.py --self-test` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | NMEA-01,03-09 | unit | `python src/nixichron_gps.py --self-test` | ❌ W0 | ⬜ pending |
| 01-01-03 | 01 | 1 | VAL-01,02,03 | integration | `python src/nixichron_gps.py --self-test` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `src/nixichron_gps.py` — script with checksum, builder, and self-test functions

*Self-test is built into the script itself — no separate test framework needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Checksum matches external calculator | VAL-03 | Requires cross-referencing with an online NMEA checksum tool | Copy a generated sentence, paste into an NMEA checksum calculator, verify match |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 1s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
