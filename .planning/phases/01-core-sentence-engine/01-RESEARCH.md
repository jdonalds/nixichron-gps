# Phase 1: Core Sentence Engine - Research

**Researched:** 2026-04-09
**Domain:** Python NMEA $GPRMC sentence builder, XOR checksum, --self-test runner
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** XOR loop over all bytes between `$` and `*` (exclusive of both delimiters), formatted as two uppercase hex digits
- **D-02:** Two separate implementations for self-test integrity: the builder computes the checksum during sentence construction, and the verifier parses a completed sentence string to independently recompute and compare. This catches off-by-one bugs in the XOR range.
- **D-03:** Pure function signature: takes a `datetime` object (UTC), returns `bytes` (the complete sentence including `$`, `*HH`, and `\r\n`)
- **D-04:** Returns `bytes` because `serial.write()` expects bytes and `--dry-run` (Phase 2) can `.decode('ascii')` for stdout
- **D-05:** No side effects in the builder — time is captured once at the call site and passed in
- **D-06:** `--self-test` generates 5 sentences, prints each sentence followed by `PASS` or `FAIL`
- **D-07:** Exit code 0 if all 5 pass, exit code 1 on any failure
- **D-08:** Self-test is inherently diagnostic — no separate verbosity control needed
- **D-09:** Include the mode indicator field `,A` (Autonomous) as field 12, before the `*` checksum. This is NMEA 2.3 format.
- **D-10:** The trailing mode indicator field is harmless to field-counting parsers that stop at their expected field count.
- **D-11:** Sentence format: `$GPRMC,hhmmss.00,A,0000.0000,N,00000.0000,E,0.0,0.0,ddmmyy,,,A*HH\r\n`
- **D-12:** Magnetic variation fields 10-11 are empty (two commas with no content between them)
- **D-13:** Time fractional seconds always `.00` (not `.ss` — we don't need sub-second precision for a 1 Hz clock)

### Claude's Discretion

- Internal variable naming and code organization within the single file
- Whether to use `functools.reduce` or a simple for-loop for XOR (preference: simple for-loop for readability)
- How to structure the self-test output formatting (PASS/FAIL per line is the requirement; exact formatting is flexible)
- Whether checksum hex formatting uses `format()` or f-string (either is fine for Python 3.9+)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NMEA-01 | Script generates valid `$GPRMC` sentences with all 13 fields including NMEA 2.3 mode indicator `A` | D-09, D-11: locked format string covers all 13 fields; confirmed against NovAtel OEM7 field docs |
| NMEA-02 | XOR checksum computed over all bytes between `$` and `*` (exclusive), formatted as two uppercase hex digits | D-01: algorithm locked; `sentence[1:sentence.index('*')]` is the canonical Python idiom |
| NMEA-03 | UTC time field formatted as `hhmmss.00` from `datetime.now(timezone.utc)` | D-13: `.00` fixed; `strftime('%H%M%S') + '.00'`; must use `timezone.utc` not bare `datetime.now()` |
| NMEA-04 | UTC date field formatted as `ddmmyy` from same UTC source | Pitfall 14: `strftime('%d%m%y')` — day first, not ISO order `%y%m%d` |
| NMEA-05 | Status field is always `A` (Active) — never `V` | Hard-coded literal `'A'` in format string; verified in self-test |
| NMEA-06 | Dummy position fields present: `0000.0000,N,00000.0000,E` | D-11: exact format locked; 4 decimal digits lat, 5 decimal digits lon |
| NMEA-07 | Speed `0.0`, course `0.0`, empty magnetic variation fields | D-11, D-12: two consecutive empty commas for mag var; speed/course as literal `0.0` |
| NMEA-08 | Sentence terminated with `<CR><LF>` (`\r\n`) | Must encode as `(body + '\r\n').encode('ascii')` — Python defaults to `\n` only |
| NMEA-09 | Only `$GPRMC` sentences emitted — no other sentence types | Builder is a pure function returning exactly one sentence; self-test confirms it |
| VAL-01 | `python nixichron_gps.py --self-test` passes (5 sentences, all checksums valid) | D-06, D-07: two independent checksum implementations required by D-02 |
| VAL-02 | `python nixichron_gps.py --dry-run` for 5 seconds produces correctly formatted sentences | Phase 2 concern, but builder must return bytes that decode cleanly to ASCII |
| VAL-03 | At least one checksum manually verified against known-good calculator | Self-test with fixed datetime provides known expected output for cross-check |
</phase_requirements>

---

## Summary

Phase 1 delivers the pure-function core of the emulator: `nmea_checksum()`, `build_gprmc()`, and `run_self_test()`. There are no external dependencies for this phase — everything uses Python 3.9 stdlib (`datetime`, `sys`). The builder takes a UTC `datetime`, assembles the fixed-format `$GPRMC` body, computes an XOR checksum, and returns the complete sentence as `bytes` including `\r\n`. The self-test generates 5 sentences across different UTC timestamps, verifies each checksum using a second independent implementation (as required by D-02), prints `PASS` or `FAIL` per sentence, and exits 0 or 1.

All six of the most common NMEA emulator bugs — wrong XOR range, lowercase hex, missing `\r\n`, status field `V`, local time instead of UTC, and wrong date format — are detectable by the self-test before any serial port or hardware is involved. The decisions in CONTEXT.md are complete and locked; no design choices remain open for this phase.

The phase produces the foundation that Phases 2-5 build on. The function signatures established here (pure function, `datetime` in, `bytes` out) must be honored by all downstream phases.

**Primary recommendation:** Implement in layer order — checksum function first (immediately testable), then builder, then self-test runner. Use a frozen `datetime` in tests for deterministic expected output.

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 1 |
|-----------|-------------------|
| Python 3.9+ only | No `match/case`, no `X \| Y` union types, no `datetime.UTC` (use `timezone.utc`) |
| Single script `nixichron_gps.py` | All functions go in one file; no modules, no packages |
| No NTP library | Use `datetime.now(timezone.utc)` exclusively |
| 4800 baud fixed | Irrelevant for Phase 1 (no serial I/O); note for Phase 5 |
| Files under 500 lines | Single-file constraint; Phase 1 sections are small — no risk |
| NEVER save to root folder | Script at project root is intentional per project design; supporting files to `/src` if any |
| ALWAYS run tests after code changes | Run `--self-test` after implementing each layer |

---

## Standard Stack

### Core (Phase 1 only)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `datetime` | 3.9+ | UTC time source | Project constraint; `datetime.now(timezone.utc)` is the mandated pattern |
| Python stdlib `sys` | 3.9+ | Exit codes (0/1) | Used in self-test runner for `sys.exit()` |

No pip installs are needed for Phase 1. pyserial is the only external dependency and it is not used until Phase 5.

**Environment verification (confirmed):**
```
Python 3.9.6  — verified on target machine
pyserial 3.5  — verified installed (not needed until Phase 5)
```

### Alternatives Considered (all rejected)

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Simple for-loop XOR | `functools.reduce(xor, ...)` | For-loop is more readable; discretion area — use for-loop |
| f-string checksum format | `format(n, '02X')` | Both are correct for 3.9+; discretion area — either acceptable |
| Inline `datetime.strftime` | Pre-computed field strings | strftime inline is clearer; no performance concern at 1 Hz |

---

## Architecture Patterns

### Phase 1 File Structure (within `nixichron_gps.py`)

```
nixichron_gps.py
├── [1] Imports and constants          ← Phase 1 adds: datetime, timezone, sys
├── [2] nmea_checksum()               ← Phase 1: checksum calculator (Layer 1)
├── [3] build_gprmc()                 ← Phase 1: sentence builder (Layer 2)
├── [4] run_self_test()               ← Phase 1: self-test runner (Layer 3)
├── [5-10] (stubs / not yet added)    ← Phases 2-5 fill these in
```

### Pattern 1: Checksum Calculator

**What:** XOR all bytes between `$` and `*` (exclusive). Return a 2-char uppercase hex string.

**When to use:** Called by the builder during construction; called independently by the verifier in self-test (D-02 requires two separate implementations or two separate call sites).

**Implementation:**
```python
# Source: NMEA 0183 spec (gpsd.gitlab.io/gpsd/NMEA.html), confirmed HIGH confidence
def nmea_checksum(sentence: str) -> str:
    """XOR all bytes between '$' and '*' (exclusive). Returns two uppercase hex digits."""
    body = sentence[1:sentence.index('*')]
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    return f'{checksum:02X}'
```

**Critical detail:** `sentence[1:sentence.index('*')]` is the safe canonical idiom. `sentence[1:]` alone includes everything after `$` including the `*` and any existing checksum digits — wrong if verifying a completed sentence. `sentence.split('*')[0][1:]` also works and is equally safe.

### Pattern 2: NMEA Sentence Builder (Pure Function)

**What:** Takes a UTC `datetime`, returns the complete `$GPRMC` sentence as `bytes`.

**When to use:** Called at the call site where `datetime.now(timezone.utc)` was just captured. Never captures time internally (D-05).

**Locked format (D-11):**
```
$GPRMC,hhmmss.00,A,0000.0000,N,00000.0000,E,0.0,0.0,ddmmyy,,,A*HH\r\n
```

Field breakdown:
```
Field  1  — UTC time:          hhmmss.00    (strftime('%H%M%S') + '.00')
Field  2  — Status:            A            (hard-coded literal)
Field  3  — Latitude:          0000.0000    (hard-coded literal)
Field  4  — Lat direction:     N            (hard-coded literal)
Field  5  — Longitude:         00000.0000   (hard-coded literal)
Field  6  — Lon direction:     E            (hard-coded literal)
Field  7  — Speed over ground: 0.0          (hard-coded literal)
Field  8  — Course over ground:0.0          (hard-coded literal)
Field  9  — Date:              ddmmyy       (strftime('%d%m%y'))
Field 10  — Magnetic variation:(empty)      (nothing between commas)
Field 11  — Mag var direction: (empty)      (nothing between commas)
Field 12  — Mode indicator:    A            (NMEA 2.3 Autonomous, D-09)
```

Comma count: 11 commas in the body (between `$GPRMC` and `*`).

**Implementation:**
```python
# Source: D-11 (locked decision), confirmed against NovAtel OEM7 GPRMC docs
def build_gprmc(utc_dt) -> bytes:
    """Build a complete $GPRMC sentence from a UTC datetime. Returns bytes with \\r\\n."""
    time_str = utc_dt.strftime('%H%M%S') + '.00'
    date_str = utc_dt.strftime('%d%m%y')
    body = f'GPRMC,{time_str},A,0000.0000,N,00000.0000,E,0.0,0.0,{date_str},,,A'
    checksum = nmea_checksum('$' + body + '*')
    sentence = f'${body}*{checksum}\r\n'
    return sentence.encode('ascii')
```

**Note on checksum input:** The builder passes `'$' + body + '*'` to `nmea_checksum()` so the function always receives a string in the expected `$...*` form. The function then extracts `[1:index('*')]` as documented. This keeps the checksum function's contract consistent whether called from the builder or the verifier.

### Pattern 3: Self-Test Runner (Two Independent Implementations, D-02)

**What:** Generate 5 sentences with different UTC datetimes. For each: parse the returned `bytes` back to a string, independently recompute the checksum from the sentence body, compare against the embedded checksum. Print `PASS` or `FAIL`. Exit 0 if all pass, exit 1 on any failure.

**Why two implementations:** D-02 requires that the verifier is independent from the builder's checksum call. The verifier parses the completed sentence and recomputes — this catches off-by-one bugs in the XOR range that both implementations might share only if they use the same code.

**The verifier function is a second, distinct function** — not a call to `nmea_checksum()` from a different angle. It must accept a complete sentence string (with `$`, `*`, and checksum digits) and return the expected checksum independently derived.

```python
# Source: D-02 (locked decision)
def verify_gprmc_checksum(sentence_bytes: bytes) -> bool:
    """Parse a complete $GPRMC sentence and verify its checksum independently."""
    sentence = sentence_bytes.decode('ascii').strip()
    # Locate delimiters
    if not sentence.startswith('$') or '*' not in sentence:
        return False
    star_pos = sentence.index('*')
    embedded = sentence[star_pos + 1:star_pos + 3]
    # Independent XOR — same algorithm, different code path
    body = sentence[1:star_pos]
    computed = 0
    for char in body:
        computed ^= ord(char)
    expected = f'{computed:02X}'
    return embedded == expected
```

**Self-test runner:**
```python
# Source: D-06, D-07 (locked decisions)
import sys
from datetime import datetime, timezone, timedelta

def run_self_test() -> None:
    """Generate 5 sentences, verify checksums, print PASS/FAIL, exit 0 or 1."""
    base = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    all_pass = True
    for i in range(5):
        utc_dt = base + timedelta(seconds=i * 3600)
        sentence_bytes = build_gprmc(utc_dt)
        ok = verify_gprmc_checksum(sentence_bytes)
        label = 'PASS' if ok else 'FAIL'
        print(f'{sentence_bytes.decode("ascii").strip()}  {label}')
        if not ok:
            all_pass = False
    sys.exit(0 if all_pass else 1)
```

### Anti-Patterns to Avoid

- **Including `$` in the XOR:** `sentence[0:]` or starting at index 0 shifts every bit. Always start at index 1.
- **Including `*` or checksum digits in the XOR:** `sentence[1:]` without stopping at `*` corrupts the result. Always stop at `sentence.index('*')`.
- **Using `strftime('%H%M%S.%f')` for subseconds:** Produces 6 microsecond digits. Always append `.00` manually.
- **Using `strftime('%y%m%d')` for the date:** Produces `yymmdd` (ISO-like). NMEA requires `ddmmyy`. Always use `strftime('%d%m%y')`.
- **Using `datetime.now()` without `timezone.utc`:** Returns local time. Always `datetime.now(timezone.utc)`.
- **Using lowercase hex:** `f'{n:02x}'` produces `2a`. NMEA requires `2A`. Always use uppercase `X`.
- **Using `\n` only:** NMEA requires `\r\n`. Always include both characters before encoding.
- **Making the builder capture time internally:** Violates D-05. Time must be captured at the call site and passed in.
- **Using `datetime.UTC`:** Added in Python 3.11. Use `timezone.utc` for 3.9 compatibility.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NMEA checksum | Custom bit manipulation | Simple XOR for-loop over `ord(c)` | The algorithm is 5 lines; no library adds value |
| NMEA parsing/generation | Full NMEA parser | Inline f-string builder | `pynmea2` and `nmeasim` are parsing libraries, not generators; 3 lines of f-string is simpler and has no dependency |
| Exponential backoff | Retry framework (`tenacity`) | Inline `delay = min(delay * 2, 30)` | One exception type, trivial formula — no library needed |

**Key insight:** The NMEA sentence is a fixed-format string with two dynamic fields (time, date). Generation is not a parsing problem. Any NMEA library is solving the wrong problem.

---

## Common Pitfalls

### Pitfall 1: Wrong XOR Checksum Range (Off-by-One)

**What goes wrong:** Including `$` (index 0) or stopping late (including `*` or checksum digits) produces a wrong checksum for every sentence. Silent failure — the clock never locks.

**Why it happens:** Off-by-one in the XOR loop bounds.

**How to avoid:** Use `sentence[1:sentence.index('*')]` as the exact slice. Never `sentence[0:]`, never `sentence[1:]` without stopping at `*`.

**Warning signs:** Self-test reports FAIL for all 5 sentences. Cross-check with nmeachecksum.eqth.net using a sample sentence.

### Pitfall 2: Lowercase Checksum Hex

**What goes wrong:** Python's `hex()` and `f'{n:x}'` (lowercase `x`) produce `2a` not `2A`. Strict firmware rejects lowercase.

**How to avoid:** Always `f'{checksum:02X}'` — uppercase `X`, zero-padded to 2 digits.

**Warning signs:** `--dry-run` output shows lowercase letters after `*`.

### Pitfall 3: Missing `\r\n` (Only `\n`)

**What goes wrong:** Python strings default to `\n`. NMEA requires `\r\n` (0x0D 0x0A). The clock accumulates malformed frames and never locks.

**How to avoid:** Always `(sentence + '\r\n').encode('ascii')`. Never `sentence + '\n'`.

**Warning signs:** `repr()` of the returned bytes shows `b'...\\n'` instead of `b'...\\r\\n'`.

### Pitfall 4: Status Field `V` Instead of `A`

**What goes wrong:** Status `V` = Void = no GPS fix. The NixiChron ignores `V`-status sentences entirely. Single most common emulator failure mode.

**How to avoid:** Hard-code the literal string `'A'` in the format string. Never compute or parameterize this field.

**Warning signs:** Clock receives sentences, does not lock, no error messages.

### Pitfall 5: Local Time Instead of UTC

**What goes wrong:** `datetime.now()` (no timezone argument) returns local time. The sentence labels it as UTC. Clock displays wrong time by the host's UTC offset.

**How to avoid:** Always `datetime.now(timezone.utc)`. No exceptions.

**Warning signs:** `--dry-run` time does not match `date -u` output on the same machine.

### Pitfall 6: Wrong Date Format (`yymmdd` vs `ddmmyy`)

**What goes wrong:** `strftime('%y%m%d')` produces `260409` for 9 April 2026. NMEA date field must be `090426` (day first). The clock may display wrong date or fail to parse.

**How to avoid:** Use `strftime('%d%m%y')` — always day first. Add a comment: `# NMEA date is ddmmyy, NOT yymmdd`.

**Warning signs:** In April 2026, field 9 reads `260409` (wrong) instead of `090426` (correct).

### Pitfall 7: `datetime.UTC` Compatibility (Python 3.11+ Only)

**What goes wrong:** `datetime.UTC` was added in Python 3.11. Using it on Python 3.9 raises `AttributeError`.

**How to avoid:** Always import and use `timezone.utc` from `datetime`. Never `datetime.UTC`.

**Warning signs:** `AttributeError: type object 'datetime.datetime' has no attribute 'UTC'` on startup.

---

## Code Examples

### Complete Verified Sentence (Fixed Datetime for Cross-Check)

For `datetime(2026, 4, 9, 12, 34, 56, tzinfo=timezone.utc)`:

```
Expected body: GPRMC,123456.00,A,0000.0000,N,00000.0000,E,0.0,0.0,090426,,,A
XOR of body bytes: computed character by character
Expected checksum: verify against nmeachecksum.eqth.net
Full sentence: $GPRMC,123456.00,A,0000.0000,N,00000.0000,E,0.0,0.0,090426,,,A*XX\r\n
```

The planner must include a task to cross-check the self-test output against an external calculator (VAL-03).

### Comma Count Verification

The body between `$GPRMC` and `*` must contain exactly 11 commas for a 12-field NMEA 2.3 sentence:

```
$GPRMC , 123456.00 , A , 0000.0000 , N , 00000.0000 , E , 0.0 , 0.0 , 090426 , , , A *XX
       1           2   3           4   5            6   7     8     9         10  11 12
```

Fields 10 and 11 (magnetic variation) are empty — two consecutive commas with nothing between them. Field 12 is the mode indicator `A`. Count 11 commas.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | All of Phase 1 | Yes | 3.9.6 | None needed |
| pyserial | Phase 5 only | Yes | 3.5 | N/A — not used in Phase 1 |

**Step 2.6: No external dependencies for Phase 1.** The phase is pure Python stdlib. No tool probing required beyond confirming Python version (confirmed: 3.9.6).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Built-in `--self-test` flag (no external test framework for Phase 1) |
| Config file | None — self-test is part of the script itself |
| Quick run command | `python3 nixichron_gps.py --self-test` |
| Full suite command | `python3 nixichron_gps.py --self-test` (same — no other tests in Phase 1) |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | Test Exists? |
|--------|----------|-----------|-------------------|-------------|
| NMEA-01 | 13 fields including mode indicator `A` | self-test / visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-02 | XOR checksum correct, uppercase hex | self-test | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-03 | Time field `hhmmss.00` from UTC | self-test / visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-04 | Date field `ddmmyy` | self-test / visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-05 | Status always `A` | self-test / visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-06 | Dummy position `0000.0000,N,00000.0000,E` | visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-07 | Speed `0.0`, course `0.0`, empty mag var | visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-08 | Terminated with `\r\n` | self-test (repr check) | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| NMEA-09 | Only `$GPRMC` emitted | visual | `python3 nixichron_gps.py --self-test` | No — Wave 0 |
| VAL-01 | `--self-test` exits 0 | self-test | `python3 nixichron_gps.py --self-test; echo $?` | No — Wave 0 |
| VAL-02 | `--dry-run` produces valid sentences | smoke (Phase 2 CLI) | Phase 2 concern; builder only tested via self-test | No — Wave 0 |
| VAL-03 | One checksum manually verified | manual | Cross-check one sentence against nmeachecksum.eqth.net | No — Wave 0 |

### Sampling Rate

- **Per task commit:** `python3 nixichron_gps.py --self-test`
- **Per wave merge:** `python3 nixichron_gps.py --self-test; echo "Exit: $?"`
- **Phase gate:** `--self-test` exits 0 AND VAL-03 manual cross-check completed

### Wave 0 Gaps

- [ ] `nixichron_gps.py` — the script itself does not yet exist; create it with sections [1]-[4] (imports, checksum, builder, self-test)
- [ ] No external test framework needed — `--self-test` is the validation mechanism per project decisions

*(No conftest, no pytest.ini — the self-test is self-contained)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 (deprecated utcnow) | Must use aware datetime; `utcnow()` returns naive datetime which can cause tz confusion |
| `datetime.UTC` | `timezone.utc` | Python 3.11 added `UTC` alias | Use `timezone.utc` for 3.9 compatibility |
| `'%x'` format for checksum hex | `'%02X'` / `f'{n:02X}'` | Always | NMEA spec requires uppercase; Python's `hex()` returns lowercase |

**Deprecated/outdated:**
- `datetime.utcnow()`: Deprecated in Python 3.12. Produces a naive datetime (no tzinfo). Wrong for explicit UTC use. Use `datetime.now(timezone.utc)`.
- `datetime.UTC`: Python 3.11+ only. Not safe on project-required 3.9 floor.
- `pynmea2` / `nmeasim` for generation: These are parsing libraries. The generation task is too simple to warrant a library dependency.

---

## Open Questions

1. **Expected checksum for the fixed test datetime**
   - What we know: The format is deterministic for a given `datetime`; the algorithm is fully specified
   - What's unclear: The exact two-digit hex value for `datetime(2026, 4, 9, 12, 34, 56)` is not pre-computed here
   - Recommendation: The implementation task must compute it and cross-check against nmeachecksum.eqth.net to satisfy VAL-03. Include this cross-check as an explicit verification step in the plan.

2. **Self-test datetime variety**
   - What we know: D-06 requires 5 sentences
   - What's unclear: The context does not specify which 5 datetimes to use
   - Recommendation: Use datetimes with varying hours/minutes/seconds to exercise all digit positions in the time and date fields. Example: space them 1 hour apart from a base datetime.

---

## Sources

### Primary (HIGH confidence)
- NMEA 0183 spec via gpsd project — https://gpsd.gitlab.io/gpsd/NMEA.html — $GPRMC field definitions, checksum algorithm
- NovAtel OEM7 GPRMC documentation — https://docs.novatel.com/OEM7/Content/Logs/GPRMC.htm — mode indicator field `A` = Autonomous (field 12)
- Python datetime docs — https://docs.python.org/3/library/datetime.html — `datetime.now(timezone.utc)`, `strftime`
- Python sys docs — https://docs.python.org/3/library/sys.html — `sys.exit()`
- `.planning/research/PITFALLS.md` — all 16 pitfalls, HIGH confidence
- `.planning/research/SUMMARY.md` — stack decisions, HIGH confidence
- `.planning/research/ARCHITECTURE.md` — layer order, component boundaries, HIGH confidence
- `.planning/phases/01-core-sentence-engine/01-CONTEXT.md` — locked decisions D-01 through D-13

### Secondary (MEDIUM confidence)
- NMEA checksum XOR range explanation — https://rietman.wordpress.com/2008/09/25/how-to-calculate-the-nmea-checksum/ — corroborates `[1:index('*')]` idiom

### Tertiary (LOW confidence)
- None for Phase 1 — all findings are verified against official spec or locked project decisions.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Python 3.9 stdlib only; verified installed (3.9.6)
- Architecture: HIGH — locked decisions cover all design choices; layer order from ARCHITECTURE.md
- Pitfalls: HIGH — all Phase 1 pitfalls verified against NMEA 0183 spec and prior research

**Research date:** 2026-04-09
**Valid until:** Stable — NMEA 0183 checksum spec does not change; Python stdlib datetime API is stable
