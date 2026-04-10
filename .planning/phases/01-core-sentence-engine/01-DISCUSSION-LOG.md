# Phase 1: Core Sentence Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-09
**Phase:** 01-core-sentence-engine
**Areas discussed:** Checksum approach, Self-test design, Sentence builder, Mode indicator

---

## Gray Area Selection

User was presented with 4 gray areas and delegated all decisions to Claude ("you choose"). All four areas resolved by Claude's judgment based on NMEA standard requirements, research findings, and project constraints.

## Checksum Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Single implementation | One checksum function, test against hardcoded expected values | |
| Two separate implementations | Builder computes during construction; verifier parses and recomputes independently | ✓ |

**User's choice:** Claude's discretion
**Notes:** Two implementations catch off-by-one bugs in XOR range that a single implementation would miss.

## Self-test Design

| Option | Description | Selected |
|--------|-------------|----------|
| Quiet (exit code only) | Just exit 0/1 with no output | |
| Per-sentence PASS/FAIL | Print each sentence + PASS/FAIL, exit 0 if all pass | ✓ |
| Verbose with field breakdown | Show each field parsed separately | |

**User's choice:** Claude's discretion
**Notes:** Per-sentence output balances debuggability with simplicity. Self-test is inherently diagnostic.

## Sentence Builder

| Option | Description | Selected |
|--------|-------------|----------|
| Return str | Caller encodes to bytes before serial write | |
| Return bytes | Builder returns complete bytes including CRLF | ✓ |

**User's choice:** Claude's discretion
**Notes:** `serial.write()` wants bytes; dry-run can `.decode('ascii')`. Pure function taking datetime, returning bytes.

## Mode Indicator

| Option | Description | Selected |
|--------|-------------|----------|
| Omit (NMEA 2.1) | 11 fields only, compatible with oldest parsers | |
| Include `,A` (NMEA 2.3) | 12 fields with Autonomous mode indicator | ✓ |

**User's choice:** Claude's discretion
**Notes:** Trailing field is harmless to field-counting parsers. Easy to remove if hardware testing reveals issues.

## Claude's Discretion

- All four areas were delegated to Claude
- Internal naming, code organization, formatting approach

## Deferred Ideas

None — discussion stayed within phase scope
