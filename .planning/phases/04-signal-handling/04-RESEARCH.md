# Phase 4: Signal Handling - Research

**Researched:** 2026-04-09
**Domain:** Python stdlib `signal` module — flag-based SIGTERM/SIGINT shutdown with `finally` port cleanup
**Confidence:** HIGH

---

## Summary

Phase 4 adds clean shutdown to the running daemon. When the OS delivers SIGTERM (from `systemctl stop` or `kill`) or SIGINT (from Ctrl-C), the script must stop its main loop without leaving the USB serial adapter in a locked state. The pattern is well-established and fully documented in the Python stdlib: a module-level boolean flag (`_shutdown`) is set inside a minimal signal handler; the main loop polls that flag at each iteration; a `try/finally` block in `main()` guarantees port cleanup regardless of how the loop exits.

No new libraries are required. The entire implementation is Python stdlib (`signal` module). The only code changes are: add the `_shutdown` flag and `_handle_signal()` function, register them for both signals, replace `while True` with `while not _shutdown`, and wrap the loop body in `try/finally`. Tests verify the behavior by spawning a subprocess, sending SIGTERM or SIGINT, and asserting clean exit code plus no traceback in stderr.

The main subtlety is ordering: signal handlers must be registered before the main loop starts, and the `finally` block is the only correct place for port cleanup — not inside the handler. Raising an exception from the handler (a common beginner approach) is explicitly discouraged by Python docs due to GIL interactions with blocking I/O.

**Primary recommendation:** Set `_shutdown = True` in the handler; poll `while not _shutdown` in main; close port in `finally`. No other approach is correct for this use case.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIG-01 | SIGTERM and SIGINT caught cleanly — sets a shutdown flag, main loop exits | Flag-based handler pattern confirmed in Python signal docs (HIGH). `signal.signal()` registers handler; `_shutdown` flag is checked at top of each loop iteration. |
| SIG-02 | Serial port closed in `finally` block on shutdown (prevents locked USB adapter state) | `try/finally` pattern around main loop confirmed in Python docs and architecture research (HIGH). Port close must NOT be in handler — only in `finally`. |
</phase_requirements>

---

## Project Constraints (from CLAUDE.md)

- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary for achieving the goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER save working files, tests, or docs to the root folder — use `/src`, `/tests`, `/docs`, `/config`, `/scripts`, `/examples`
- ALWAYS read a file before editing it
- NEVER commit secrets, credentials, or .env files
- ALWAYS run tests after making code changes
- ALWAYS verify build succeeds before committing
- Files under 500 lines
- Use typed interfaces for all public APIs
- Prefer TDD London School (mock-first) for new code
- Input validation at system boundaries

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `signal` (stdlib) | Python 3.9 | Register SIGTERM/SIGINT handlers | Only mechanism for OS signal interception in Python; no alternatives needed |
| `signal.SIGTERM` | Python 3.9 | Systemd stop / `kill <pid>` | Standard Unix process termination signal |
| `signal.SIGINT` | Python 3.9 | Ctrl-C keyboard interrupt | Keyboard interrupt; default CPython handler raises KeyboardInterrupt |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `subprocess` (stdlib) | Python 3.9 | Test harness: spawn process, send signal | Already used in test_timing.py and test_cli.py for subprocess integration tests |
| `signal.SIGTERM` / `os.kill` | Python 3.9 | Test harness: deliver signal to subprocess | Send SIGTERM to subprocess PID in integration tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Boolean flag + `while not _shutdown` | Raising `SystemExit` from handler | Exception from handler is discouraged by Python docs — can deadlock if raised during blocking I/O |
| Boolean flag + `while not _shutdown` | `threading.Event` | Overkill; single-threaded loop only needs a plain bool |
| `finally` block for port close | Close in signal handler | Wrong — handler runs on signal delivery, not on loop exit; cannot guarantee cleanup ordering |

**Installation:** No additional packages. Phase 4 is pure stdlib.

---

## Architecture Patterns

### Recommended Project Structure

No structural change to the file layout. Phase 4 adds code to `src/nixichron_gps.py` only:

```
src/
└── nixichron_gps.py    # Adds: _shutdown flag, _handle_signal(), signal registration,
                        #        while not _shutdown, try/finally in main()
tests/
└── test_signal.py      # New: SIG-01 and SIG-02 subprocess integration tests
```

### Pattern 1: Flag-Based Signal Handler

**What:** A module-level boolean `_shutdown` is set to `True` inside a minimal handler. The handler does nothing else — no I/O, no logging, no cleanup.

**When to use:** Any single-threaded daemon loop that needs clean shutdown on SIGTERM/SIGINT.

**Example:**
```python
# Source: Python signal docs — https://docs.python.org/3/library/signal.html
import signal

_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True

signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)
```

**Where to register:** In `main()` before the loop starts (not at module level), so the handler is only active when the daemon is running. Module-level registration would fire during `--self-test` and test imports. Alternatively, registration can be at module level if the handler is unconditionally safe — but placing it in `main()` is cleaner for this codebase's pattern.

**Important:** After `signal.signal(signal.SIGINT, _handle_signal)` is called, CPython's default `KeyboardInterrupt` exception is suppressed. Ctrl-C will set `_shutdown = True` instead of raising an exception. This is the desired behavior for a daemon.

### Pattern 2: Loop Sentinel + try/finally

**What:** Replace `while True` with `while not _shutdown`. Wrap the entire loop in `try/finally` so port cleanup runs on both normal and signal-interrupted exit.

**When to use:** Always, when a loop has resources that must be released on exit.

**Example:**
```python
# Source: Python docs pattern — https://docs.python.org/3/library/signal.html
def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    if args.self_test:
        run_self_test()

    # Register handlers inside main() so they are active only during daemon run
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    port = None
    try:
        while not _shutdown:
            sleep_until_next_second()
            utc_dt = datetime.now(timezone.utc)
            sentence = build_gprmc(utc_dt)
            logger.debug(sentence.decode('ascii').strip())

            if args.dry_run:
                sys.stdout.buffer.write(sentence)
                sys.stdout.buffer.flush()
            else:
                # Phase 5: port.write(sentence)
                pass
    finally:
        if port is not None:
            port.close()
            logger.info('Serial port closed.')
```

**Key points:**
- `port = None` initialized before `try` so `finally` can check `is not None` safely (Phase 5 will assign it)
- `finally` runs even if the loop exits normally (future code path) — not just on signal
- No port exists yet in Phase 4 (Phase 5 opens it), so `finally` body is a no-op placeholder
- `logger.info` in `finally` is safe — it is NOT in the signal handler

### Anti-Patterns to Avoid

- **Raising exceptions from signal handler:** `raise SystemExit()` inside `_handle_signal` can deadlock if the signal fires while CPython holds the GIL for a blocking `write()`. The Python signal docs explicitly warn against this.
- **Closing port inside the signal handler:** Handler runs on signal delivery, not at a safe point in the loop. Port may be mid-write. Only set the flag; close in `finally`.
- **Registering at module level without guarding:** If `signal.signal()` is called at module import time, signals will be intercepted during `--self-test` runs and test imports. Register in `main()`.
- **Ignoring `_shutdown` inside the sleep:** `sleep_until_next_second()` can sleep up to ~1 second. The process will appear to hang briefly before exiting. This is acceptable for a 1 Hz loop — no special wakeup mechanism needed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Signal interception | Custom `ctypes` signal trap or `SIGALRM` polling | `signal.signal()` with flag | The stdlib does this correctly and portably |
| Loop exit on signal | Threading event, asyncio, custom poll loop | `while not _shutdown` boolean sentinel | Single-threaded 1 Hz loop needs nothing more complex |
| Guaranteed cleanup | `atexit` handler | `try/finally` | `atexit` does not run on SIGTERM (only on normal exit and SIGINT if handler re-raises); `finally` always runs |

**Key insight:** The signal handling problem in a 1 Hz synchronous loop has a one-line solution in the handler and a three-line solution in main. Any more complexity is over-engineering.

---

## Common Pitfalls

### Pitfall 1: KeyboardInterrupt Survives the Signal Override
**What goes wrong:** Developer registers `_handle_signal` for SIGTERM but forgets SIGINT. Ctrl-C still raises `KeyboardInterrupt` and prints a traceback instead of clean exit.
**Why it happens:** CPython's default SIGINT handler raises `KeyboardInterrupt`. Registering a custom handler for SIGTERM does not affect SIGINT.
**How to avoid:** Register `_handle_signal` for both `signal.SIGTERM` and `signal.SIGINT` in the same call sequence.
**Warning signs:** Test sends SIGTERM and passes; manual Ctrl-C still shows traceback.

### Pitfall 2: Signal Registered in Wrong Scope
**What goes wrong:** `signal.signal()` called at module level. Signal is active during `--self-test`, test collection, and all imports. The `_shutdown` flag may interfere with test teardown.
**Why it happens:** Convenience — module-level code runs once and is easy to write.
**How to avoid:** Register signals inside `main()`, after `parse_args()` and `setup_logging()`, before the loop.
**Warning signs:** `--self-test` exits unexpectedly; tests behave differently when imported vs. run standalone.

### Pitfall 3: finally Block Raises Because port is None
**What goes wrong:** Phase 5 is not yet implemented. `finally: port.close()` raises `AttributeError: 'NoneType' object has no attribute 'close'`.
**Why it happens:** `port` was not initialized before the `try` block, or the guard `if port is not None` was omitted.
**How to avoid:** Initialize `port = None` before `try`. Write `finally: if port is not None: port.close()`.
**Warning signs:** Clean SIGTERM produces a secondary traceback from `finally`.

### Pitfall 4: Test Sends Signal Too Early (Race Condition)
**What goes wrong:** Subprocess integration test sends SIGTERM before the process has started its loop. Process exits without proving the loop exited cleanly.
**Why it happens:** Subprocess spawn is asynchronous; the main loop may not have started when the test sends the signal.
**How to avoid:** Wait for at least one `$GPRMC` line on stdout before sending SIGTERM. This guarantees the loop is running. Use `stdout=PIPE` and read until the first line, then send the signal.
**Warning signs:** Test is flaky; sometimes passes (signal lands in loop), sometimes the process exits with code 0 immediately without producing output.

### Pitfall 5: Checking Exit Code Is Not Enough
**What goes wrong:** Test asserts `proc.returncode == 0` but does not check stderr. A traceback could appear in stderr while exit code is still 0 (if `finally` runs but an exception was caught somewhere).
**Why it happens:** `sys.exit(0)` overrides exception-based exit codes in some paths.
**How to avoid:** Assert both `returncode == 0` AND `b'Traceback' not in stderr`.

---

## Code Examples

Verified patterns from official sources:

### Signal Handler Registration (SIG-01)
```python
# Source: https://docs.python.org/3/library/signal.html
import signal

_shutdown = False

def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
```

### Loop Sentinel (SIG-01)
```python
# Replace: while True:
while not _shutdown:
    sleep_until_next_second()
    # ... rest of loop body ...
```

### try/finally Port Cleanup (SIG-02)
```python
# Source: Python docs finally-block pattern
port = None
try:
    while not _shutdown:
        # loop body
        pass
finally:
    if port is not None:
        port.close()
        logger.info('Serial port closed.')
```

### Integration Test Pattern (SIG-01 test)
```python
# Source: Pattern established in test_timing.py and test_cli.py
import subprocess, signal, sys, time

proc = subprocess.Popen(
    [sys.executable, str(SRC_PATH), '--dry-run'],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Wait for loop to start: read first $GPRMC line
first_line = b''
while not first_line.startswith(b'$GPRMC'):
    chunk = proc.stdout.read(64)
    if not chunk:
        break
    first_line += chunk

proc.send_signal(signal.SIGTERM)
stdout, stderr = proc.communicate(timeout=3)

assert proc.returncode == 0
assert b'Traceback' not in stderr
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raise `KeyboardInterrupt` from SIGINT handler | Set boolean flag; suppress exception | Python 2 era | No traceback on Ctrl-C; clean exit path |
| `atexit` for cleanup | `try/finally` | Python 2.5+ | `atexit` misses SIGTERM; `finally` catches all exit paths |
| `signal.pause()` for blocking | `while not _shutdown` with `time.sleep()` | N/A | Loop has work to do; cannot block indefinitely |

**Deprecated/outdated:**
- Using `signal.SIG_DFL` to reset SIGINT to default and catching `KeyboardInterrupt`: works but produces traceback noise; the flag pattern is cleaner.
- `atexit.register(port.close)`: does not fire on SIGTERM; not safe for this use case.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 4 is purely code changes to `src/nixichron_gps.py`. No external dependencies beyond the Python 3.9 stdlib are required. `signal` is built into CPython. No tools, services, or CLIs need to be probed.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (version in use — confirmed by `.pytest_cache/` present) |
| Config file | None detected — pytest discovers tests/ directory by convention |
| Quick run command | `python3 -m pytest tests/test_signal.py -x -q` |
| Full suite command | `python3 -m pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIG-01 | SIGTERM causes loop exit, clean return code 0, no traceback | integration (subprocess) | `python3 -m pytest tests/test_signal.py::TestSignalHandling::test_sigterm_clean_exit -x` | No — Wave 0 |
| SIG-01 | SIGINT causes loop exit, clean return code 0, no traceback | integration (subprocess) | `python3 -m pytest tests/test_signal.py::TestSignalHandling::test_sigint_clean_exit -x` | No — Wave 0 |
| SIG-01 | Loop polls `_shutdown` flag (structural: `while not _shutdown` present in source) | unit (source inspection) | `python3 -m pytest tests/test_signal.py::TestShutdownFlag::test_loop_uses_shutdown_flag -x` | No — Wave 0 |
| SIG-02 | `finally` block present in `main()` source (structural guard) | unit (source inspection) | `python3 -m pytest tests/test_signal.py::TestShutdownFlag::test_finally_block_present -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_signal.py -x -q`
- **Per wave merge:** `python3 -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_signal.py` — covers SIG-01 (subprocess integration) and SIG-02 (source inspection)

No new framework install required — pytest is already in use.

---

## Existing Test Infrastructure

The codebase already uses a consistent subprocess integration test pattern. Phase 4 tests must follow the same conventions:

| Convention | Where Established | Must Follow |
|------------|-------------------|-------------|
| `_load_module()` with `importlib.util.spec_from_file_location` | `test_timing.py`, `test_cli.py` | Yes — unit tests that need module import |
| `PROJECT_ROOT = pathlib.Path(__file__).parent.parent` | Both existing test files | Yes |
| `SRC_PATH = PROJECT_ROOT / 'src' / 'nixichron_gps.py'` | Both existing test files | Yes |
| `subprocess.Popen` + `communicate(timeout=N)` + `send_signal(signal.SIGTERM)` | `test_timing.py`, `test_cli.py` | Yes — subprocess integration tests |
| `sys.modules['nixichron_gps'] = mod` registration | `test_timing.py` | Only if `unittest.mock.patch` targeting module by name is needed |

---

## Open Questions

1. **Signal registration location: module level vs. main()**
   - What we know: The existing code has all side-effectful setup in `main()` (logging, arg parsing). The architecture research says "register in main()".
   - What's unclear: Whether tests that import the module (not run it) would be affected if registration were at module level.
   - Recommendation: Register in `main()`, after `setup_logging()` and `parse_args()`, before the loop. Consistent with the codebase's pattern of keeping side effects out of module scope.

2. **Dry-run exit code when SIGTERM received**
   - What we know: Current code has no signal handling; SIGTERM likely causes a non-zero exit via the OS default handler.
   - What's unclear: Whether the existing `test_timing.py::TestTimingIntegration::test_timestamps_advance_by_one_second` will break if the exit code changes after Phase 4 (it currently sends SIGTERM via `communicate(timeout=12)` expiry).
   - Recommendation: After Phase 4, `--dry-run` + SIGTERM should exit 0. Verify existing test_timing integration test still passes — it does not currently assert returncode, so it should be unaffected.

3. **`_shutdown` variable naming: module-level vs. passed as argument**
   - What we know: Architecture research specifies `_shutdown` as a module-level global (underscore prefix = private-by-convention). The existing codebase uses no globals.
   - What's unclear: Whether the planner might prefer passing a flag object to avoid globals.
   - Recommendation: Use the module-level global per architecture spec and Python signal docs examples. This is the only way for a signal handler (which receives only `signum, frame`) to communicate with the main loop without passing objects through module state.

---

## Sources

### Primary (HIGH confidence)
- [Python signal module docs](https://docs.python.org/3/library/signal.html) — `signal.signal()` API, handler constraints, flag-based pattern
- `src/nixichron_gps.py` (read directly) — exact current `main()` structure, loop body, `while True`, `else: pass` placeholder
- `tests/test_timing.py`, `tests/test_cli.py` (read directly) — established subprocess test patterns to follow
- `.planning/research/ARCHITECTURE.md` (read directly) — signal handler pattern, layer 6 spec, anti-patterns
- `.planning/research/SUMMARY.md` (read directly) — "Signal flag pattern is in official Python signal docs" [HIGH confidence]

### Secondary (MEDIUM confidence)
- [Python signal docs note on handlers](https://docs.python.org/3/library/signal.html#notes-on-signal-handlers) — GIL interaction warning; handlers execute between atomic bytecode instructions
- Architecture research citation: [Graceful SIGTERM in Python](https://dnmtechs.com/graceful-sigterm-signal-handling-in-python-3-best-practices-and-implementation/) — sentinel flag pattern [MEDIUM]

### Tertiary (LOW confidence)
- None identified. Signal handling for a single-threaded Python loop is a fully documented, stable stdlib domain.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — `signal` module is stdlib, fully documented, no external packages
- Architecture: HIGH — flag-based handler + while sentinel + try/finally is the canonical Python pattern; confirmed in official docs and project architecture research
- Pitfalls: HIGH — all pitfalls verified against Python signal docs or derived from reading existing test code patterns in this codebase
- Test patterns: HIGH — derived directly from reading existing test files in this repo

**Research date:** 2026-04-09
**Valid until:** Stable indefinitely — Python stdlib signal API has not changed in 3.x; no third-party libraries involved
