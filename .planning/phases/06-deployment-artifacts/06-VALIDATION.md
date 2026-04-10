---
phase: 6
slug: deployment-artifacts
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | grep/file checks + existing pytest suite |
| **Config file** | N/A — static files |
| **Quick run command** | `test -f requirements.txt && test -f nixichron-gps.service && test -f README.md && echo OK` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~40 seconds (existing suite) |

---

## Sampling Rate

- **After every task commit:** File existence + grep checks
- **After every plan wave:** Full test suite (must not regress)
- **Max feedback latency:** 5 seconds (grep checks are instant)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| pip install works | DEPLOY-01 | Requires clean venv | `python3 -m venv /tmp/test-env && /tmp/test-env/bin/pip install -r requirements.txt` |
| systemd unit loads | DEPLOY-02 | Requires Linux + systemd | `systemd-analyze verify nixichron-gps.service` |
| Wiring diagram accuracy | DEPLOY-04 | Visual inspection | Compare ASCII diagram to physical connector |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
