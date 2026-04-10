---
phase: 3
slug: timing-loop
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-10
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + subprocess integration |
| **Config file** | tests/ directory |
| **Quick run command** | `python3 -m pytest tests/test_timing.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~20 seconds (includes 10s timing integration test + Phase 1-2 tests) |

---

## Sampling Rate

- **After every task commit:** Run `python3 src/nixichron_gps.py --self-test`
- **After every plan wave:** Run full test suite
- **Before `/gsd:verify-work`:** Full suite green + 10s dry-run timing check
- **Max feedback latency:** 20 seconds

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| $ char transmitted at second boundary | TIME-03 | Requires oscilloscope/logic analyzer for precise measurement | Run --dry-run, observe timestamps match `date -u` within ~100ms |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
