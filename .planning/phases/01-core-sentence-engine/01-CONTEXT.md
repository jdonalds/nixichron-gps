# Phase 1: Core Sentence Engine - Context

**Gathered:** 2026-04-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate syntactically correct $GPRMC NMEA sentences with valid XOR checksums, proven correct by `--self-test`. No serial I/O, no timing loop, no CLI shell — just the sentence builder, checksum calculator, and self-test validator. This phase produces the pure-function core that all later phases build on.

</domain>

<decisions>
## Implementation Decisions

### Checksum computation
- **D-01:** XOR loop over all bytes between `$` and `*` (exclusive of both delimiters), formatted as two uppercase hex digits
- **D-02:** Two separate implementations for self-test integrity: the builder computes the checksum during sentence construction, and the verifier parses a completed sentence string to independently recompute and compare. This catches off-by-one bugs in the XOR range.

### Sentence builder function
- **D-03:** Pure function signature: takes a `datetime` object (UTC), returns `bytes` (the complete sentence including `$`, `*HH`, and `\r\n`)
- **D-04:** Returns `bytes` because `serial.write()` expects bytes and `--dry-run` (Phase 2) can `.decode('ascii')` for stdout
- **D-05:** No side effects in the builder — time is captured once at the call site and passed in

### Self-test mode
- **D-06:** `--self-test` generates 5 sentences, prints each sentence followed by `PASS` or `FAIL`
- **D-07:** Exit code 0 if all 5 pass, exit code 1 on any failure
- **D-08:** Self-test is inherently diagnostic — no separate verbosity control needed

### NMEA 2.3 mode indicator
- **D-09:** Include the mode indicator field `,A` (Autonomous) as field 12, before the `*` checksum. This is NMEA 2.3 format.
- **D-10:** Rationale: the trailing field is harmless to field-counting parsers that stop at their expected field count. If hardware testing in Phase 5 reveals an issue, removing it is a one-character change.

### Field layout (locked by NMEA standard + requirements)
- **D-11:** Sentence format: `$GPRMC,hhmmss.00,A,0000.0000,N,00000.0000,E,0.0,0.0,ddmmyy,,,A*HH\r\n`
- **D-12:** Magnetic variation fields 10-11 are empty (two commas with no content between them)
- **D-13:** Time fractional seconds always `.00` (not `.ss` — we don't need sub-second precision for a 1 Hz clock)

### Claude's Discretion
- Internal variable naming and code organization within the single file
- Whether to use `functools.reduce` or a simple for-loop for XOR (preference: simple for-loop for readability)
- How to structure the self-test output formatting (PASS/FAIL per line is the requirement; exact formatting is flexible)
- Whether checksum hex formatting uses `format()` or f-string (either is fine for Python 3.9+)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

No external specs — requirements are fully captured in decisions above and in:

### Project requirements
- `.planning/REQUIREMENTS.md` — Full v1 requirements with NMEA-01 through NMEA-09, VAL-01 through VAL-03
- `.planning/PROJECT.md` — Project context, constraints, key decisions

### Research findings
- `.planning/research/FEATURES.md` — Table stakes feature analysis, NixiChron lock behavior notes
- `.planning/research/ARCHITECTURE.md` — Component breakdown and build order rationale
- `.planning/research/PITFALLS.md` — Checksum off-by-one, status field, timing pitfalls
- `.planning/research/SUMMARY.md` — Synthesized research findings

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing code

### Established Patterns
- None yet — Phase 1 establishes the patterns for the project

### Integration Points
- The sentence builder function is the core that Phase 2 (CLI/dry-run), Phase 3 (timing loop), and Phase 5 (serial I/O) all call
- The self-test verifier function is reused by `--self-test` in Phase 2's CLI wiring

</code_context>

<specifics>
## Specific Ideas

- Builder is a drop-in replacement for the Haicom HI-204III GPS puck output — sentence format must be byte-identical to what the original puck would send
- PIC firmware triggers 1 PPS off the leading edge of the `$` character — while timing is Phase 3's concern, the builder should not add any prefix bytes before `$`
- The NixiChron's PIC has a small buffer — only one sentence type ($GPRMC) can be sent. The builder must never emit anything else.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-core-sentence-engine*
*Context gathered: 2026-04-09*
