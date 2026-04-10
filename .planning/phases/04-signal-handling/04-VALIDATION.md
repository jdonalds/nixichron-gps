---
phase: 4
slug: signal-handling
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + subprocess signal tests |
| **Config file** | tests/ directory |
| **Quick run command** | `python3 -m pytest tests/test_signal.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~30 seconds (includes timing + signal integration tests) |

---

## Sampling Rate

- **After every task commit:** Run `python3 src/nixichron_gps.py --self-test`
- **After every plan wave:** Run full test suite
- **Before `/gsd:verify-work`:** Full suite green
- **Max feedback latency:** 30 seconds

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No traceback on Ctrl-C | SIG-01 | Visual verification of clean exit | Run `--dry-run`, press Ctrl-C, confirm no traceback |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
