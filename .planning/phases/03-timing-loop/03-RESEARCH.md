# Phase 3: Timing Loop - Research

**Researched:** 2026-04-09
**Domain:** Python deadline-based 1 Hz synchronous loop, UTC second boundary alignment
**Confidence:** HIGH

## Summary

Phase 3 replaces the naive `time.sleep(1)` placeholder in `main()` with a deadline-based loop that aligns sentence emission to the UTC second boundary. The core technique is simple: compute the integer ceiling of the current wall-clock time (`math.ceil(time.time())`), then sleep the fractional-second remainder. Because the deadline is an absolute point in time rather than a relative duration, execution overhead from sentence building and I/O dispatch does not accumulate as drift.

The critical hardware constraint that motivates this phase: the PIC firmware inside the NixiChron clock triggers its 1 PPS signal from the leading edge of the `$` character on the wire. The `$` must be transmitted at (or as close as possible to) the UTC second boundary. At 4800 baud, the `$` reaches the firmware approximately 2 ms after `port.write()` is called. There is no further timing adjustment possible in userspace Python. The task is to sleep until the boundary, then call `write()` immediately upon waking.

The entire implementation is pure Python stdlib: `time.time()`, `time.sleep()`, and `math.ceil()`. No external libraries are needed. The pattern is well-established in Python real-time tooling. The main function change is surgical: remove `time.sleep(1)`, add `sleep_until_next_second()` before the `datetime.now()` capture, and capture the timestamp after waking (not before sleeping).

**Primary recommendation:** Use `next_tick = math.ceil(time.time()); time.sleep(max(0.0, next_tick - time.time()))` as the canonical deadline sleep. Call it at the top of the loop, before `datetime.now(timezone.utc)`.

## Project Constraints (from CLAUDE.md)

The project CLAUDE.md is the workspace-level RuFlo V3 config. Directives that apply to this phase:

- NEVER create files unless absolutely necessary — Phase 3 adds only a helper function; no new files needed beyond the test file
- ALWAYS prefer editing an existing file to creating a new one — timing helper goes into `src/nixichron_gps.py`
- Use `/src` for source code, `/tests` for test files
- Prefer TDD London School (mock-first) for new code — write `tests/test_timing.py` before modifying `nixichron_gps.py`
- ALWAYS run tests after making code changes
- Keep files under 500 lines — `src/nixichron_gps.py` is currently ~200 lines; adding a timing helper keeps it well under limit

Note: The CLAUDE.md `npm run build` / `npm test` / `npm run lint` commands are RuFlo boilerplate for JS projects. This is a pure Python project. The actual test command is `python3 -m pytest tests/` (confirmed working, 24 tests pass).

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TIME-01 | Sentences emitted at exactly 1 Hz, aligned to the UTC second boundary | Deadline-based sleep to `math.ceil(time.time())` corrects for per-iteration overhead; alignment verified by checking sentence timestamps against wall clock |
| TIME-02 | Deadline-based timing loop (not naive `sleep(1)`) to prevent drift accumulation | `math.ceil(time.time())` pattern is the canonical Python solution; documented in ARCHITECTURE.md; replaces the existing `time.sleep(1)` stub |
| TIME-03 | The `$` character (leading edge = clock's 1 PPS trigger) should be transmitted as close to the second boundary as possible | Achieved by sleeping to the boundary first, then capturing `datetime.now(timezone.utc)` and calling `write()` immediately — minimizing code between wake and write |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `time` (stdlib) | Python 3.9+ | Wall-clock read (`time.time()`) and sleep (`time.sleep()`) | Only sleep mechanism in stdlib; internally uses OS monotonic clock for duration so NTP corrections don't shorten a sleep |
| `math` (stdlib) | Python 3.9+ | `math.ceil()` to compute next integer second | Clean, readable ceiling operation; no third-party dep |
| `datetime` (stdlib) | Python 3.9+ | UTC datetime capture after waking, for sentence timestamp | Already imported in the file |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `unittest.mock.patch` | Python 3.9+ | Freeze `time.time()` in unit tests | Use in `test_timing.py` to test sleep logic without real delays |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `math.ceil(time.time())` | `int(time.time()) + 1` | Same result for non-integer times; `math.ceil` is more explicit about intent. Do not use `+1` blindly: if called at an exact integer second it would skip a full second. `math.ceil` of an exact integer returns the same integer — correct behavior. |
| `time.sleep(max(0, ...))` | bare `time.sleep(next_tick - now)` | Without `max(0, ...)`, a negative duration crashes if `time.time()` is called fractionally after an integer second (e.g., thread scheduling jitter). Always clamp. |
| Dedicated scheduler (`sched`, APScheduler) | manual deadline loop | Overkill for a single-task 1 Hz loop; adds import, state, and learning cost. stdlib loop is 4 lines. |

**Installation:** No new packages needed — pure stdlib.

## Architecture Patterns

### Recommended Project Structure
```
src/
└── nixichron_gps.py    # Single flat file — add sleep_until_next_second() as Layer 5

tests/
├── test_timing.py      # New: Phase 3 timing tests (RED then GREEN pattern)
├── test_cli.py         # Existing Phase 2 tests
└── test_verify_and_self_test.py  # Existing Phase 1 tests
```

### Pattern 1: Deadline-Based Sleep (canonical form)

**What:** Compute the next integer UTC second as an absolute timestamp, sleep the fractional remainder, then act immediately on wake.

**When to use:** Any 1 Hz synchronous loop where the action must align to a wall-clock boundary rather than execute at a relative interval.

**Example:**
```python
# Source: ARCHITECTURE.md + Python time docs (HIGH confidence)
import time
import math

def sleep_until_next_second() -> None:
    """Sleep until the start of the next UTC second boundary.

    Uses math.ceil(time.time()) so the target is always an integer second.
    Clamps to max(0.0, ...) to handle the rare case of being called at an
    exact integer second (avoids negative sleep or sleeping a full extra second).
    """
    now = time.time()
    next_tick = math.ceil(now)
    time.sleep(max(0.0, next_tick - now))
```

### Pattern 2: Correct Loop Order — Sleep Before Timestamp Capture

**What:** The loop sleeps to the boundary FIRST, then calls `datetime.now(timezone.utc)` AFTER waking. The timestamp for the sentence reflects the second that has just arrived, not the previous second.

**When to use:** Every iteration of the main loop — mandatory ordering.

**Example:**
```python
# Source: ARCHITECTURE.md anti-pattern 3 (HIGH confidence)
while not _shutdown:
    sleep_until_next_second()          # wait for boundary
    utc_dt = datetime.now(timezone.utc)  # capture AFTER wake, not before
    sentence = build_gprmc(utc_dt)
    if args.dry_run:
        sys.stdout.buffer.write(sentence)
        sys.stdout.buffer.flush()
    else:
        pass  # Phase 5: serial write
```

### Pattern 3: Edge Case — Called at an Exact Integer Second

**What:** If `time.time()` returns a float that is exactly an integer (or within floating-point epsilon of one), `math.ceil()` returns that same integer. `next_tick - now` is ~0. `max(0.0, ...)` ensures `time.sleep(0.0)` is called, which yields the GIL and returns immediately. The next `datetime.now()` captures the correct second.

**Why it matters:** Without `max(0.0, ...)`, a slightly negative value from floating-point rounding would raise `ValueError: sleep length must be non-negative`.

### Anti-Patterns to Avoid

- **Sleeping before timestamp capture:** Captures stale time. The sentence timestamp will be off by one second. The clock's 1 PPS trigger fires based on the sentence's time field, so a wrong timestamp means the clock displays the wrong second.
- **Using `int(time.time()) + 1` instead of `math.ceil`:** If called exactly on an integer second (rare but possible after scheduling jitter), this overshoots by 1 full second, introducing a 1-second bubble in the output stream.
- **Using `datetime.microsecond` to compute sleep duration:** The ARCHITECTURE.md shows this alternative pattern (`1.0 - now.microsecond / 1_000_000`). It is equivalent but slightly less precise because it routes through `datetime` objects instead of `time.time()`. Use `math.ceil(time.time())` as the canonical form — both are in the project research, but the `math.ceil` form is more explicit.
- **Not clamping with `max(0.0, ...)`:** Risks `ValueError` on exact-second calls or after thread scheduling delays cause the computed sleep to go negative.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Drift correction | Custom drift accumulator tracking long-term error | `math.ceil(time.time())` deadline per iteration | Each iteration independently corrects itself; no state needed |
| Precision timing | `time.monotonic()` arithmetic, OS timer APIs | `time.time()` + `math.ceil` | Wall-clock alignment is the goal, not monotonic interval; `time.sleep()` uses monotonic internally anyway |
| Scheduler | `sched.scheduler`, APScheduler, asyncio loop | Manual 4-line deadline loop | A 1-task 1 Hz loop needs no scheduler abstraction |

**Key insight:** The deadline pattern self-corrects every iteration. Even if one iteration runs 50 ms long, the next `math.ceil(time.time())` computes the correct next boundary. There is no accumulated error to drain.

## Common Pitfalls

### Pitfall 1: Timestamp Captured Before Sleep
**What goes wrong:** `utc_dt = datetime.now(timezone.utc)` is called, then `sleep_until_next_second()`, then `build_gprmc(utc_dt)`. The sentence timestamp is the second that ended, not the second beginning now. The NixiChron receives `GPRMC,...,120000.00,...` at the moment the 12:00:01 second boundary fires, meaning the clock's display lags behind by one second.
**Why it happens:** Intuitive to capture data before sleeping, but the sleep crosses a second boundary.
**How to avoid:** Always call `sleep_until_next_second()` first, then `datetime.now(timezone.utc)`.
**Warning signs:** In `--dry-run`, subtract consecutive timestamps: if they are 1.0 s apart but the wall clock shows the sentences are arriving 1 second late, this is the cause.

### Pitfall 2: Naive Sleep Accumulates Drift
**What goes wrong:** `time.sleep(1)` sleeps for 1 second, but sentence build + `write()` + `flush()` + logging take ~5–20 ms. After 50 iterations the emitter is ~0.5–1 second behind the UTC second boundary. The clock's PPS sync degrades.
**Why it happens:** `time.sleep(1)` is a relative interval, not an absolute deadline.
**How to avoid:** Use the deadline pattern. This is what TIME-02 requires.
**Warning signs:** Over a 60-second `--dry-run`, the first sentence timestamp should match `date -u` to within ~50 ms. With naive sleep, it drifts to 500+ ms within a few minutes.

### Pitfall 3: `math.ceil` on Integer Input
**What goes wrong:** Code calls `math.ceil(1775792747.0)` (exact integer float). Returns `1775792747`. Computes `1775792747 - 1775792747.0 == 0.0`. `time.sleep(0.0)` returns immediately. Everything is fine — but only if the `max(0.0, ...)` guard is present to handle the case where floating-point arithmetic makes this slightly negative.
**Why it happens:** Floating-point representation means `time.time()` can return values with tiny sub-microsecond artifacts.
**How to avoid:** Always write `time.sleep(max(0.0, next_tick - time.time()))` — not `time.sleep(next_tick - time.time())`.

### Pitfall 4: Testing Real Sleep Durations in Unit Tests
**What goes wrong:** A test for `sleep_until_next_second()` calls it for real and blocks the test runner for up to 1 second per test iteration. With multiple test cases, the suite takes 5–10 seconds unnecessarily.
**Why it happens:** Forgetting that unit tests must be fast and deterministic.
**How to avoid:** Mock `time.time()` to return a controlled value (e.g., `1234.750`), then assert `time.sleep` was called with approximately `0.25`. Use `unittest.mock.patch`.

## Code Examples

Verified patterns from official sources and project ARCHITECTURE.md:

### Canonical Deadline Sleep Helper
```python
# Source: .planning/research/ARCHITECTURE.md (HIGH confidence)
import time
import math

def sleep_until_next_second() -> None:
    """Sleep until the start of the next UTC second boundary.

    Deadline-based: computes next integer second from wall clock, sleeps the
    fractional remainder. Self-correcting per iteration — no drift accumulation.
    """
    now = time.time()
    next_tick = math.ceil(now)
    time.sleep(max(0.0, next_tick - now))
```

### Main Loop with Correct Ordering
```python
# Source: .planning/research/ARCHITECTURE.md anti-pattern 3 (HIGH confidence)
while not _shutdown:
    sleep_until_next_second()
    utc_dt = datetime.now(timezone.utc)   # capture AFTER sleep, not before
    sentence = build_gprmc(utc_dt)
    logger.debug(sentence.decode('ascii').strip())
    if args.dry_run:
        sys.stdout.buffer.write(sentence)
        sys.stdout.buffer.flush()
    else:
        pass  # Phase 5: serial write
```

### Unit Test Pattern — Mock time.time and time.sleep
```python
# Source: Python unittest.mock docs (HIGH confidence)
from unittest.mock import patch

def test_sleep_until_next_second_sleeps_remainder():
    """sleep_until_next_second sleeps the fractional complement of the current second."""
    # Simulate being 0.25 seconds into the current second
    with patch('nixichron_gps.time.time', return_value=1234.750), \
         patch('nixichron_gps.time.sleep') as mock_sleep:
        sleep_until_next_second()
        mock_sleep.assert_called_once()
        actual_duration = mock_sleep.call_args[0][0]
        assert abs(actual_duration - 0.25) < 1e-6
```

### Integration Test — Timestamp Advances by 1 Second per Sentence
```python
# Source: Phase 3 success criteria (ROADMAP.md)
# Run --dry-run for ~3 seconds and check consecutive timestamps differ by 1 s
import subprocess, signal, sys, re
from datetime import datetime

proc = subprocess.Popen(
    [sys.executable, 'src/nixichron_gps.py', '--dry-run'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
try:
    stdout, _ = proc.communicate(timeout=4)
except subprocess.TimeoutExpired:
    proc.send_signal(signal.SIGTERM)
    stdout, _ = proc.communicate()

lines = [l for l in stdout.split(b'\r\n') if l.startswith(b'$GPRMC')]
assert len(lines) >= 3
times = []
for line in lines:
    m = re.search(rb'\$GPRMC,(\d{6})\.00,', line)
    if m:
        t = m.group(1).decode()
        times.append(datetime.strptime(t, '%H%M%S'))
for i in range(1, len(times)):
    delta = (times[i] - times[i-1]).seconds
    assert delta == 1, f"Expected 1s gap, got {delta}s between {times[i-1]} and {times[i]}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `time.sleep(1)` | `math.ceil(time.time())` deadline | Pre-2010 Python practice | Eliminates drift accumulation entirely |
| Capture UTC before sleep | Capture UTC after sleep | Standard pattern in NMEA emulators | Ensures sentence timestamp matches the second being announced |

**Deprecated/outdated:**
- `time.clock()`: Removed in Python 3.8. Use `time.perf_counter()` for benchmarking, `time.time()` for wall-clock alignment. Do not use `time.clock()`.
- `datetime.utcnow()`: Deprecated in Python 3.12 (aware vs naive ambiguity). Already excluded by project constraint — always use `datetime.now(timezone.utc)`.

## Open Questions

1. **Sleep jitter on the target Linux host under load**
   - What we know: `time.sleep()` precision on Linux is typically ±1–5 ms under light load. At 4800 baud, the `$` takes ~2 ms to reach the PIC after `write()`. Total jitter budget before the PPS trigger is affected is on the order of tens of milliseconds — the NixiChron likely has tolerance for this.
   - What's unclear: The NixiChron firmware's PPS debounce window is unknown. If the system is under heavy CPU load, sleep jitter could exceed 50 ms.
   - Recommendation: Accept userspace jitter. A Raspberry Pi running only this daemon will be well within tolerance. Document the limitation in Phase 6 README troubleshooting if needed.

2. **Should `sleep_until_next_second()` use `time.time()` or `time.monotonic()` for the sleep duration?**
   - What we know: `time.time()` can jump backward or forward during NTP step corrections. `time.sleep()` internally uses the monotonic clock for the duration, so the sleep itself is immune to NTP jumps. However, the deadline calculation (`next_tick - time.time()`) uses wall-clock time — an NTP step during the call could make the calculation wrong.
   - What's unclear: How large are NTP step corrections on a well-synced host? On a Raspberry Pi with `systemd-timesyncd`, steps are rare and small (<1s) after initial sync.
   - Recommendation: Use `time.time()` for deadline calculation (wall-clock alignment is the goal). NTP step risk is negligible for this use case.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Runtime | ✓ | 3.x (darwin) | — |
| `math` (stdlib) | `math.ceil` | ✓ | stdlib | — |
| `time` (stdlib) | deadline sleep | ✓ | stdlib | — |
| `pytest` | test runner | ✓ | detected (24 tests passing) | — |

No external dependencies required by Phase 3. Step 2.6 SKIPPED for external services — this phase is code-only.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | none — pytest discovers `tests/` automatically |
| Quick run command | `python3 -m pytest tests/test_timing.py -x` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TIME-01 | Sentences emitted at 1 Hz with timestamps advancing by 1 s | integration | `python3 -m pytest tests/test_timing.py::TestTimingIntegration -x` | Wave 0 |
| TIME-02 | Loop uses `math.ceil(time.time())` deadline, not `sleep(1)` | unit | `python3 -m pytest tests/test_timing.py::TestSleepUntilNextSecond -x` | Wave 0 |
| TIME-03 | Timestamp captured after sleep, not before | unit | `python3 -m pytest tests/test_timing.py::TestLoopOrder -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_timing.py -x`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green (currently 24 tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_timing.py` — covers TIME-01, TIME-02, TIME-03; does not exist yet

## Sources

### Primary (HIGH confidence)
- `.planning/research/ARCHITECTURE.md` — Top-of-second timing pattern, anti-patterns 1 and 3, canonical `sleep_until_next_second()` implementation
- `.planning/research/SUMMARY.md` — Pitfall 4 (naive sleep drift), recommended stack
- `src/nixichron_gps.py` — Current `time.sleep(1)` stub location (line 196), import list, Layer 5 insertion point
- [Python `time` module docs](https://docs.python.org/3/library/time.html) — `time.time()`, `time.sleep()` monotonic internals
- [Python `math` module docs](https://docs.python.org/3/library/math.html) — `math.ceil()` behavior on integer floats

### Secondary (MEDIUM confidence)
- [Python `unittest.mock` docs](https://docs.python.org/3/library/unittest.mock.html) — `patch` decorator for freezing `time.time()`

### Tertiary (LOW confidence)
- NixiChron PPS debounce window tolerance — inferred from NMEA standard practice; not confirmed against actual firmware

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure stdlib, no version risk
- Architecture: HIGH — pattern verified in ARCHITECTURE.md and confirmed by empirical `math.ceil` test above
- Pitfalls: HIGH — all derived from ARCHITECTURE.md anti-patterns plus direct code inspection of the `time.sleep(1)` stub

**Research date:** 2026-04-09
**Valid until:** 2026-10-09 (stdlib patterns are stable; math.ceil behavior does not change)
