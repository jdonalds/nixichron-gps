# Phase 5: Serial I/O and Reconnect - Research

**Researched:** 2026-04-09
**Domain:** pyserial serial port I/O, exponential backoff reconnect, Python exception handling
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SER-01 | Serial port opened at 4800 baud, 8N1, no flow control (xonxoff=False, rtscts=False) | pyserial Serial() constructor parameters fully documented; exact call pattern confirmed |
| SER-02 | Serial port configurable via `--port` CLI arg, `GPS_PORT` env var, or default `/dev/ttyUSB0` | `parse_args()` already captures `args.port`; Phase 5 just reads it — no new CLI work needed |
| SER-03 | Graceful handling of serial port disconnects with exponential backoff retry (1s, 2s, 4s... capped at 30s) | Standard stdlib pattern: `delay = min(delay * 2, 30)`; inline — no library needed |
| SER-04 | Reconnect logged at WARNING level; successful reconnect logged at INFO level | Named logger already wired; this is a two-line logging addition |
</phase_requirements>

---

## Summary

Phase 5 replaces the `else: pass` placeholder in `main()` with a complete serial write path. The core loop structure (signal handling, timing, `try/finally` port close) is already in place from Phases 3 and 4. This phase adds three things: (1) a `serial.Serial()` open call using the parameters required by the NixiChron hardware, (2) a `port.write(sentence)` call wrapped in a broad `SerialException` catch, and (3) an exponential backoff reconnect loop that runs whenever the port is absent or drops.

The implementation is entirely inline — no new functions need to be created, no new modules, no new files. The only external dependency, `pyserial==3.5`, is already installed on the development machine (`pip3 show pyserial` confirms version 3.5). The entire phase consists of replacing 4 lines in `nixichron_gps.py` and adding approximately 30 lines of serial open/write/reconnect logic.

The primary risk in Phase 5 is the pyserial `write_timeout` POSIX bug (issues #281, #460): spurious `SerialTimeoutException` can fire even when the port is healthy. The mitigation is to set `write_timeout=2` (to prevent indefinite blocking) but catch `SerialException` broadly for all write errors, treating any exception as a disconnect event that enters the reconnect loop.

**Primary recommendation:** Implement `open_serial()` as a helper that encapsulates the `serial.Serial()` constructor call, then replace `else: pass` in `main()` with a write-and-reconnect pattern that calls this helper from within the backoff loop.

---

## Project Constraints (from CLAUDE.md)

- Python 3.9+ — no `match/case`, no `X | Y` union types, no `datetime.UTC` (requires 3.11)
- Single flat script `nixichron_gps.py` — no package structure, no new files
- `pyserial==3.5` is the only external dependency
- 4800 baud is fixed — not configurable
- Files must stay under 500 lines
- Use typed interfaces for public APIs (type annotations on any new functions)
- TDD London School preferred — write tests first
- ALWAYS run tests after code changes
- NEVER hardcode secrets or credentials (not applicable here — no credentials)
- Use `/tests` for test files, `/src` for source code

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyserial | 3.5 | Serial port open, write, close | Only maintained cross-platform Python serial library; no viable alternative |
| serial.SerialException | (built-in) | Catch all I/O errors on port | Base class for all pyserial errors — catches open failure and write failure |
| stdlib `time` | 3.9 stdlib | Backoff `time.sleep()` calls | No third-party needed for simple delay |
| stdlib `logging` | 3.9 stdlib | WARNING on disconnect, INFO on reconnect | Already wired in existing code |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| serial.SerialTimeoutException | (built-in) | Subclass of SerialException | Caught automatically by broad `SerialException` catch — do NOT catch separately |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline backoff | `tenacity` or `backoff` library | External dependency, overkill for a 4-line loop |
| Broad `SerialException` catch | Narrow `SerialTimeoutException` catch | POSIX write_timeout bug fires spuriously; broad catch is safer |
| `write_timeout=2` | `write_timeout=None` | None blocks forever on stall; 2s surfaces errors quickly |

**Installation:**
```bash
# Already installed — no action needed
pip install pyserial==3.5
```

**Version verification:**
```
pyserial 3.5 confirmed installed: pip3 show pyserial (2026-04-09)
Latest stable remains 3.5 — pyserial GitHub has not released 3.6
```

---

## Architecture Patterns

### Where Phase 5 Code Lives

```
src/nixichron_gps.py
├── Layer 0: _shutdown flag, _handle_signal()           [Phase 4 — complete]
├── Layer 1: nmea_checksum()                            [Phase 1 — complete]
├── Layer 2: build_gprmc()                              [Phase 1 — complete]
├── Layer 3a: verify_gprmc_checksum()                   [Phase 1 — complete]
├── Layer 3b: run_self_test()                           [Phase 1 — complete]
├── Layer 4: setup_logging()                            [Phase 2 — complete]
├── Layer 5: sleep_until_next_second()                  [Phase 3 — complete]
├── Layer 6: parse_args()                               [Phase 2 — complete]
└── Layer 7: main()
    ├── port = None                                     [Phase 4 — complete]
    ├── try/finally with port.close()                   [Phase 4 — complete]
    ├── while not _shutdown: ...                        [Phase 3/4 — complete]
    │   ├── sleep_until_next_second()                   [Phase 3 — complete]
    │   ├── build_gprmc(utc_dt)                         [Phase 3 — complete]
    │   ├── if dry_run: stdout write                    [Phase 2 — complete]
    │   └── else: pass   <-- REPLACE THIS (Phase 5)
    └── NEW: open_serial() helper   <-- ADD HERE
```

### Pattern 1: Serial Open Helper

A small helper function isolates the `serial.Serial()` constructor call so tests can mock it without patching deep into `main()`.

```python
# Source: pyserial official docs https://pyserial.readthedocs.io/en/latest/pyserial.html
import serial

def open_serial(port: str) -> serial.Serial:
    """Open serial port at 4800/8N1, no flow control.

    Returns an open serial.Serial. Raises serial.SerialException on failure.
    write_timeout=2 prevents indefinite blocking on stall; dsrdtr/rtscts/xonxoff
    all False to avoid unexpected DTR/RTS toggling on NixiChron TX-only link.
    """
    return serial.Serial(
        port=port,
        baudrate=4800,
        bytesize=serial.EIGHTBITS,   # 8
        parity=serial.PARITY_NONE,   # N
        stopbits=serial.STOPBITS_ONE, # 1
        xonxoff=False,               # no software flow control
        rtscts=False,                # no RTS/CTS hardware flow control
        dsrdtr=False,                # no DSR/DTR hardware flow control
        write_timeout=2,             # surface stall; None blocks forever
    )
```

### Pattern 2: Write-with-Reconnect in main()

Replaces `else: pass` entirely. The outer `while not _shutdown` loop is already present; this adds the reconnect inner loop.

```python
# Source: pyserial GitHub + pyserial docs (SerialException)
else:
    # SER-01/02/03/04: open port with exponential backoff reconnect
    _BACKOFF_BASE = 1.0
    _BACKOFF_MAX  = 30.0
    if port is None:
        delay = _BACKOFF_BASE
        while port is None and not _shutdown:
            try:
                port = open_serial(args.port)
                logger.info('Serial port %s opened.', args.port)
                delay = _BACKOFF_BASE  # reset on success
            except serial.SerialException as e:
                logger.error('Cannot open %s: %s', args.port, e)  # LOG-02
                logger.warning('Retrying in %.0fs...', delay)       # SER-04
                time.sleep(delay)
                delay = min(delay * 2, _BACKOFF_MAX)
    if port is not None:
        try:
            port.write(sentence)
        except serial.SerialException as e:
            logger.error('Write error on %s: %s', args.port, e)    # LOG-02
            logger.warning('Port lost — reconnecting...')            # SER-04
            try:
                port.close()
            except Exception:
                pass
            port = None  # triggers re-open on next iteration
```

**Key detail:** Setting `port = None` on write failure causes the existing `if port is None` guard to re-enter the backoff loop on the very next `while not _shutdown` iteration, without any structural duplication.

**Key detail:** The `finally` block already calls `port.close()` only when `port is not None` — this guard is already correct from Phase 4. No change needed there.

### Pattern 3: Successful Reconnect Logging (SER-04)

The `logger.info('Serial port %s opened.')` call in the reconnect loop covers the "successful reconnect" case. On the first open (not a reconnect), this is identical — acceptable. The WARNING log on retry covers the SER-04 "reconnect logged at WARNING" requirement.

### Anti-Patterns to Avoid

- **Catching `SerialTimeoutException` separately:** It is a subclass of `SerialException`. Catching it separately and re-raising others changes behavior and adds pyserial POSIX bug exposure. Catch `SerialException` broadly everywhere.
- **Resetting `delay` inside the retry sleep:** Reset `delay = _BACKOFF_BASE` only after a successful `open_serial()` call, not after a sleep. Resetting during sleep defeats the backoff.
- **Calling `port.close()` in the signal handler:** The handler only sets `_shutdown = True`. Port close lives in the `finally` block. This is already correct from Phase 4.
- **Nesting the reconnect loop outside `while not _shutdown`:** The inner reconnect loop must check `not _shutdown` too, otherwise SIGTERM blocks until the port opens.
- **Using `serial.EIGHT BITS`, `serial.PARITY_NONE`, `serial.STOPBITS_ONE` as raw integers:** These constants are clearer than raw `8`, `'N'`, `1` and eliminate magic numbers. Use the named constants.
- **Moving `_BACKOFF_BASE` / `_BACKOFF_MAX` to module level:** They are used only in `main()`. Module-level placement invites them being treated as configurable; they are not. Define them as locals inside `main()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Serial port I/O | Custom `termios` / `fcntl` POSIX calls | `serial.Serial()` from pyserial | pyserial handles platform differences (macOS, Linux, Windows) and port enumeration |
| Exponential backoff library | `tenacity`, `backoff`, or `retry` third-party | Inline `delay = min(delay * 2, BACKOFF_MAX)` | 4 lines of code; no dependency justified |
| Write timeout | Custom `threading.Timer` around `port.write()` | `write_timeout=2` in constructor | pyserial handles this at the C level; threading adds complexity |

**Key insight:** The reconnect logic for this problem is simple enough (one inner while loop, one integer) that any backoff library is more complexity than it removes.

---

## Runtime State Inventory

Step 2.5 SKIPPED — this is not a rename/refactor/migration phase. Phase 5 adds new serial I/O behavior; no stored data, live service config, OS-registered state, secrets, or build artifacts use string identifiers that would change.

---

## Common Pitfalls

### Pitfall 1: `write_timeout` Spurious Exception on POSIX
**What goes wrong:** `serial.SerialTimeoutException` fires on Linux/macOS even when the port is healthy. If you catch it and treat it as a success (or re-raise as a fatal error), behavior is wrong.
**Why it happens:** pyserial issue #281 — the POSIX write_timeout implementation has a race condition. The timer can fire before the write completes, even if the write succeeds.
**How to avoid:** Set `write_timeout=2` to prevent indefinite blocking, but catch `SerialException` broadly. Do NOT catch `SerialTimeoutException` separately and do NOT let it propagate unhandled.
**Warning signs:** Script enters reconnect loop immediately after opening port even though port is connected and working.

### Pitfall 2: `tty.*` Device Blocks `open()` Forever on macOS
**What goes wrong:** `serial.Serial('/dev/tty.usbserial-XXXX', ...)` blocks indefinitely at port open time. The process hangs and never enters the main loop.
**Why it happens:** macOS `tty.*` devices wait for DCD assertion. The NixiChron is a one-way consumer and never asserts DCD.
**How to avoid:** Always use `/dev/cu.usbserial-*` on macOS. Default in `parse_args()` is `/dev/ttyUSB0` (Linux); macOS users must specify `--port /dev/cu.usbserial-XXXX`.
**Warning signs:** Script starts, prints nothing, CPU at 0%, hangs indefinitely at the open call.

### Pitfall 3: Port Not Set to `None` After Write Failure
**What goes wrong:** Write fails, `SerialException` is caught, but `port` is not set to `None`. On the next iteration, the code skips the `if port is None` reconnect guard and tries `port.write()` again on the already-broken port — failing immediately in an infinite fast loop.
**Why it happens:** Not setting `port = None` after a write failure and before calling `port.close()`.
**How to avoid:** Always set `port = None` immediately after catching the write `SerialException`, before calling `port.close()` (which may also raise).
**Warning signs:** Log floods with `Write error` at thousands of messages per second.

### Pitfall 4: Reconnect Loop Does Not Check `_shutdown`
**What goes wrong:** SIGTERM arrives while the script is in the inner reconnect `while port is None` loop. The handler sets `_shutdown = True`, but the inner loop only checks `port is None` — it never exits. The process hangs until a port appears.
**Why it happens:** Forgetting to add `and not _shutdown` to the inner reconnect loop condition.
**How to avoid:** Inner loop condition: `while port is None and not _shutdown:`.
**Warning signs:** `systemctl stop nixichron-gps` hangs at "Stopping..." indefinitely.

### Pitfall 5: DTR/RTS Toggle Confuses the Adapter at Open
**What goes wrong:** pyserial's default behavior asserts DTR/RTS on port open. Some USB-RS232 adapters generate voltage spikes on handshake lines at this moment.
**Why it happens:** pyserial defaults `dtr=True, rts=True`. The `dsrdtr=False, rtscts=False` parameters in the constructor suppress this for the handshake-negotiation protocol but do not always suppress the initial line state set.
**How to avoid:** Set `dsrdtr=False, rtscts=False` explicitly in the constructor. The NixiChron wiring uses only TX and GND so the risk is low, but explicit suppression is defensive.
**Warning signs:** Clock exhibits transient garbage display at the moment the script opens the port.

---

## Code Examples

### Complete `open_serial()` function

```python
# Source: pyserial readthedocs https://pyserial.readthedocs.io/en/latest/pyserial.html
import serial

def open_serial(port: str) -> serial.Serial:
    """Open serial port at 4800/8N1, no flow control.

    Raises serial.SerialException if port cannot be opened.
    """
    return serial.Serial(
        port=port,
        baudrate=4800,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
        write_timeout=2,
    )
```

### Backoff delay update (inline, no library)

```python
# After a failed open attempt:
time.sleep(delay)
delay = min(delay * 2, _BACKOFF_MAX)  # 1 -> 2 -> 4 -> 8 -> 16 -> 30 -> 30...

# After a successful open:
delay = _BACKOFF_BASE  # reset to 1.0
```

### SerialException catch pattern for write

```python
try:
    port.write(sentence)
except serial.SerialException as e:
    logger.error('Write error on %s: %s', args.port, e)   # LOG-02
    logger.warning('Port lost — reconnecting...')           # SER-04
    try:
        port.close()
    except Exception:
        pass
    port = None  # triggers backoff re-open on next loop iteration
```

### Import to add

```python
import serial  # pyserial — add to existing imports block
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `serial.Serial(port, baud)` positional | Named keyword args for all parameters | pyserial 2.x → 3.x | Prevents silent wrong-parameter ordering bugs |
| `write_timeout` as error mechanism | Catch `SerialException` broadly | pyserial issues #281/#460 | Eliminates spurious timeout reconnect loops |
| Manual `termios` on POSIX | `pyserial` abstraction | Established practice | Cross-platform, no platform ifdef needed |

**Deprecated/outdated:**
- `serial.Serial.write(str)` — Python 2 only. Python 3 requires `bytes`. `build_gprmc()` already returns `bytes`, so no encoding needed at the write call site.

---

## Open Questions

1. **NixiChron behavior on first valid sentence after reconnect**
   - What we know: GPS clocks typically re-lock after 1–3 valid sentences following a signal restore
   - What's unclear: NixiChron-specific lock/unlock behavior — not confirmed against firmware; sourced from neonixie-l only
   - Recommendation: Accept the uncertainty; validate empirically when hardware is present. The script's behavior (continuous 1 Hz output) is correct regardless of the clock's lock timing.

2. **macOS Sequoia driver compatibility for CH340/Prolific adapters**
   - What we know: Apple provides native FTDI dext; CH340/Prolific require vendor-supplied kexts/dexts
   - What's unclear: Current availability of CH340/Prolific dexts for macOS 15 Sequoia (2025+)
   - Recommendation: Use FTDI-chipset adapters for development. Document in README (Phase 6). Not a code-level concern.

3. **Whether `write_timeout=2` is the right value**
   - What we know: None blocks forever; 2s allows two full NMEA intervals before surfacing a stall
   - What's unclear: Whether any adapter/OS combination causes 2s to fire spuriously on a healthy port
   - Recommendation: 2s is the established community value for this use case. If spurious timeouts occur in practice, the broad `SerialException` catch degrades gracefully to a reconnect.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Runtime | ✓ | 3.9.6 | — |
| pyserial | SER-01, SER-02, SER-03, SER-04 | ✓ | 3.5 | — |
| Physical serial port / USB adapter | Hardware validation | Unknown — hardware-dependent | — | Loopback test with `socat` on macOS/Linux |
| `/dev/cu.usbserial-*` device node | macOS serial path | Hardware-dependent | — | `/dev/ttyUSB0` (Linux default) |

**Missing dependencies with no fallback:**
- Physical NixiChron hardware is needed for end-to-end validation of SER-01 success criteria #1 ("clock displays UTC time"). All other success criteria can be tested in software.

**Missing dependencies with fallback:**
- Physical USB-serial adapter: can substitute `socat -d -d pty,raw,echo=0 pty,raw,echo=0` to create a loopback pair for integration testing the reconnect logic without hardware.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Python `unittest` (stdlib, no config file needed) |
| Config file | none — tests run via `python -m unittest discover tests/` |
| Quick run command | `python -m unittest tests/test_serial.py -v` |
| Full suite command | `python -m unittest discover tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SER-01 | `open_serial()` calls `serial.Serial()` with 4800/8N1/no-flow params | unit (mock) | `python -m unittest tests/test_serial.py::TestOpenSerial -v` | ❌ Wave 0 |
| SER-02 | `open_serial(args.port)` receives the value from `parse_args()` | unit (mock) | `python -m unittest tests/test_serial.py::TestPortConfig -v` | ❌ Wave 0 |
| SER-03 | Backoff delay sequence: 1s → 2s → 4s → 8s → 16s → 30s → 30s | unit (mock) | `python -m unittest tests/test_serial.py::TestBackoff -v` | ❌ Wave 0 |
| SER-04 | WARNING logged on disconnect, INFO logged on successful (re)open | unit (mock) | `python -m unittest tests/test_serial.py::TestReconnectLogging -v` | ❌ Wave 0 |
| LOG-02 | Serial errors logged at ERROR level | unit (mock) | `python -m unittest tests/test_serial.py::TestErrorLogging -v` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m unittest tests/test_serial.py -v`
- **Per wave merge:** `python -m unittest discover tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_serial.py` — covers SER-01, SER-02, SER-03, SER-04, LOG-02
  - `TestOpenSerial`: mock `serial.Serial`, assert constructor called with exact kwargs
  - `TestPortConfig`: verify `open_serial(args.port)` receives port from `parse_args()`
  - `TestBackoff`: mock `open_serial` to fail N times then succeed; verify `time.sleep` call sequence matches 1, 2, 4...
  - `TestReconnectLogging`: verify WARNING and INFO log calls in the right order
  - `TestErrorLogging`: mock `port.write` to raise `SerialException`; verify ERROR log

*(Existing tests `test_cli.py`, `test_timing.py`, `test_signal.py`, `test_verify_and_self_test.py` are unaffected — all should remain GREEN.)*

---

## Sources

### Primary (HIGH confidence)

- pyserial readthedocs — `serial.Serial()` constructor parameters, `SerialException` class hierarchy, `write_timeout` parameter
  https://pyserial.readthedocs.io/en/latest/pyserial.html
- pyserial PyPI — version 3.5 confirmed latest stable
  https://pypi.org/project/pyserial/
- Python 3.9 docs — `logging`, `signal`, `time` stdlib modules
  https://docs.python.org/3.9/library/

### Secondary (MEDIUM confidence)

- pyserial GitHub issue #281 — write_timeout POSIX spurious SerialTimeoutException
  https://github.com/pyserial/pyserial/issues/281
- pyserial GitHub issue #460 — same POSIX write_timeout race
  https://github.com/pyserial/pyserial/issues/460
- macOS `cu.*` vs `tty.*` DCD blocking behavior
  https://www.codegenes.net/blog/what-s-the-difference-between-dev-tty-and-dev-cu-on-macos/
- neonixie-l mailing list — NixiChron 4800 baud, $GPRMC confirmed
  https://groups.google.com/g/neonixie-l/c/uxxNlaHVkC8/m/WSEAKJfPsYUJ

### Tertiary (LOW confidence / needs hardware validation)

- NixiChron lock behavior on reconnect — inferred from standard GPS clock behavior; not confirmed against actual NixiChron firmware

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pyserial 3.5 confirmed installed; constructor params from official docs
- Architecture: HIGH — replacement location (`else: pass`) and `port = None` guard are in existing code; pattern is straightforward
- Pitfalls: HIGH — write_timeout POSIX bug from official issue tracker; macOS tty/cu from official macOS serial docs; all others from phase research
- Test strategy: HIGH — unittest + mock.patch is the established pattern used in all 4 prior phases

**Research date:** 2026-04-09
**Valid until:** 2026-10-09 (pyserial 3.5 has had no release since November 2020; extremely stable)
