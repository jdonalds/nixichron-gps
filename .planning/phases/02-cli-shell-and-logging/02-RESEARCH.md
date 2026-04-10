# Phase 2: CLI Shell and Logging - Research

**Researched:** 2026-04-09
**Domain:** Python stdlib — argparse, logging, os.environ, sys.stdout.buffer
**Confidence:** HIGH

## Summary

Phase 2 wires a proper `argparse` CLI and the Python `logging` module into the existing
`src/nixichron_gps.py` single-file script. All capabilities in scope are pure Python 3.9
stdlib — no external packages, no new dependencies. The primary deliverable is replacing
the bare `if '--self-test' in sys.argv` entry point from Phase 1 with a structured
`ArgumentParser` that handles `--port`, `--dry-run`, `--self-test`, and `--verbose`/`-v`.

The `--dry-run` mode must produce correctly formatted `$GPRMC` sentences printed to
`sys.stdout.buffer` (bytes path, not text path) without opening any serial port. Phase 2
adds a naive `time.sleep(1)` loop as a placeholder — Phase 3 replaces this with a
deadline-based loop. This is intentional: keeping the timing concern in Phase 3 keeps
Phase 2 focused and fully testable without hardware.

The `GPS_PORT` environment variable must serve as the fallback for `--port`. The lookup
order is: `--port` CLI arg > `GPS_PORT` env var > `/dev/ttyUSB0` default. The `--port`
value is stored in a namespace attribute for later use by Phase 5 serial I/O; Phase 2
does not open any serial port.

**Primary recommendation:** Replace the bare `sys.argv` check at the bottom of the file
with a `parse_args()` function that returns an `argparse.Namespace`, configure `logging`
via `basicConfig` in `main()` before anything else, and route to `run_self_test()` or the
dry-run loop based on the parsed flags.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | `--port` argument to specify serial device | `add_argument('--port', default=...)` with `GPS_PORT` env fallback; stored in args.port for Phase 5 |
| CLI-02 | `--dry-run` flag prints sentences to stdout instead of serial port | `add_argument('--dry-run', action='store_true')`; dispatch to `sys.stdout.buffer.write(sentence)` |
| CLI-03 | `--self-test` flag generates 5 sentences, validates checksums, exits 0/1 | `add_argument('--self-test', action='store_true')`; calls existing `run_self_test()` |
| CLI-04 | `--verbose`/`-v` flag sets log level to DEBUG (default INFO) | `add_argument('--verbose', '-v', action='store_true')`; passed to `logging.basicConfig` |
| LOG-01 | Each sent sentence logged at DEBUG level | `logger.debug(sentence.decode('ascii').strip())` inside the dispatch path |
| LOG-02 | Serial errors logged at ERROR level | `logger.error(...)` — Phase 5 will use this; Phase 2 establishes the logger |
| LOG-03 | Uses Python `logging` module, not print statements | `logging.basicConfig` + named logger replaces bare print calls in the main dispatch path |
</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `argparse` | stdlib (3.9) | CLI flag parsing | Standard library; no alternatives needed |
| `logging` | stdlib (3.9) | Structured log output | Standard library; project constraint |
| `os` | stdlib (3.9) | `os.environ.get()` for GPS_PORT | Standard library |
| `sys` | stdlib (3.9) | `sys.stdout.buffer` for bytes dry-run output | Standard library |
| `time` | stdlib (3.9) | `time.sleep(1)` placeholder loop in dry-run | Standard library; Phase 3 replaces this |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `argparse` | `click` | click is third-party; argparse is stdlib and sufficient for 4 flags |
| `logging.basicConfig` | Structlog / loguru | Third-party; overkill for a single-file daemon with 2 log levels |
| `sys.stdout.buffer.write` | `print(sentence.decode())` | print() would strip CRLF and convert bytes; buffer.write preserves the exact bytes |

**Installation:** No new packages required. All components are Python 3.9 stdlib.

**Version verification:** Python 3.9.6 confirmed present on target machine (`python3 --version`). All stdlib modules verified available.

## Architecture Patterns

### Recommended Project Structure

The file remains a single flat script. Phase 2 adds three new sections, all below the
existing Layer 3b block:

```
src/nixichron_gps.py
  Layer 1: nmea_checksum()               [Phase 1 — unchanged]
  Layer 2: build_gprmc()                 [Phase 1 — unchanged]
  Layer 3a: verify_gprmc_checksum()      [Phase 1 — unchanged]
  Layer 3b: run_self_test()              [Phase 1 — unchanged]
  Layer 4: setup_logging(verbose)        [Phase 2 — NEW]
  Layer 5: parse_args()                  [Phase 2 — NEW]
  Layer 6: main()                        [Phase 2 — NEW stub; Phase 3-5 extend it]
  Entry point: if __name__ == '__main__' [Phase 2 — replaces bare sys.argv check]
```

### Pattern 1: GPS_PORT Env Var Fallback

**What:** `--port` CLI arg takes precedence; `GPS_PORT` environment variable is the
fallback; `/dev/ttyUSB0` is the hardcoded default.

**When to use:** Any CLI tool that needs environment variable configuration without
making it a required argument.

**Example:**
```python
# Source: Python 3.9 argparse docs (stdlib)
import os

def parse_args():
    default_port = os.environ.get('GPS_PORT', '/dev/ttyUSB0')
    parser = argparse.ArgumentParser(
        description='NixiChron GPS Emulator — feeds $GPRMC sentences to a Nixie tube clock'
    )
    parser.add_argument(
        '--port',
        default=default_port,
        help='Serial port device (default: GPS_PORT env or /dev/ttyUSB0)',
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Print sentences to stdout; do not open serial port')
    parser.add_argument('--self-test', action='store_true',
                        help='Generate 5 sentences, verify checksums, exit 0/1')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Set log level to DEBUG (default: INFO)')
    return parser.parse_args()
```

### Pattern 2: Logging Setup

**What:** `logging.basicConfig` called once in `main()` before any other code runs.
A module-level named logger is used throughout the file.

**When to use:** Any Python script that must support DEBUG/INFO/ERROR log levels from a
CLI flag.

**Example:**
```python
# Source: Python 3.9 logging docs (stdlib)
import logging

logger = logging.getLogger('nixichron')

def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
    )
```

### Pattern 3: Dry-Run Dispatch (bytes path)

**What:** Both dry-run and real serial paths accept the same `bytes` object from
`build_gprmc()`. Dry-run writes to `sys.stdout.buffer`; real path writes to the serial
port. The dispatch point is a single `if args.dry_run:` branch in `main()`.

**When to use:** Whenever a daemon needs a hardware-free test mode that uses exactly the
same data path as production.

**Example:**
```python
# Source: verified locally — sys.stdout.buffer.write preserves \r\n
import sys, time
from datetime import datetime, timezone

def main():
    args = parse_args()
    setup_logging(args.verbose)

    if args.self_test:
        run_self_test()  # exits 0 or 1

    while True:
        utc_dt = datetime.now(timezone.utc)
        sentence = build_gprmc(utc_dt)
        logger.debug(sentence.decode('ascii').strip())

        if args.dry_run:
            sys.stdout.buffer.write(sentence)
            sys.stdout.buffer.flush()
        else:
            # Phase 5 will open the serial port here
            pass

        time.sleep(1)  # Phase 3 replaces this with deadline-based sleep
```

### Pattern 4: Argparse Attribute Naming for Hyphenated Flags

**What:** argparse converts `--dry-run` to `args.dry_run` and `--self-test` to
`args.self_test`. This is automatic — hyphen becomes underscore in the `dest` attribute.

**Verification:** Confirmed with `python3 -c "..."` locally. `parse_args([])` produces
`{'port': ..., 'dry_run': False, 'self_test': False, 'verbose': False}`.

### Anti-Patterns to Avoid

- **`print()` for sentence output in non-dry-run paths:** LOG-03 explicitly requires
  `logging` module. The only acceptable `print()` call is inside `run_self_test()`,
  which is human-readable test output, not a log stream.
- **`sys.stdout.write(sentence.decode())` for dry-run:** Decoding strips CRLF awareness.
  Use `sys.stdout.buffer.write(sentence)` to preserve the exact `\r\n` bytes.
- **Global `logging.basicConfig` at module level:** Must be called from `main()` after
  `parse_args()` so verbose flag is known. Module-level basicConfig runs before flags
  are parsed and ignores the `--verbose` setting.
- **Replacing the Phase 1 `run_self_test()` print calls with logging:** The self-test
  output is human-readable pass/fail reporting, not a log stream. Keep `print()` there.
  LOG-03 targets the main dispatch loop, not the self-test reporter.
- **Opening serial port in Phase 2:** Phase 2's `else:` branch in the dispatch should
  be a `pass` or `logger.debug('serial send skipped — not yet implemented')`. Phase 5
  installs the actual `serial.Serial` call.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Flag parsing | Custom `sys.argv` loop | `argparse.ArgumentParser` | Handles `-h`, type conversion, `--` separator, and error messages automatically |
| Log level control | Manual `if verbose: print(...)` | `logging.basicConfig` + `logger.debug/info/error` | Handles formatting, handler chain, propagation — one-line level change |
| Env var default for CLI arg | Inline `os.environ.get` in default | Set `default=os.environ.get('GPS_PORT', '/dev/ttyUSB0')` in `add_argument` | Keeps env fallback co-located with the flag definition |

**Key insight:** argparse's `add_argument(default=...)` is the correct place to embed the
`os.environ.get()` call. Doing it separately creates a hidden ordering dependency.

## Common Pitfalls

### Pitfall 1: sys.stdout.write() instead of sys.stdout.buffer.write()

**What goes wrong:** `sys.stdout.write(sentence.decode('ascii'))` strips the `\r` from
`\r\n` on some platforms (Windows text mode, or Python's universal newlines). The clock
accumulates malformed frames.

**Why it happens:** `sys.stdout` is a text-mode `TextIOWrapper` that normalizes line
endings. `sys.stdout.buffer` is the underlying binary stream that preserves exact bytes.

**How to avoid:** Always use `sys.stdout.buffer.write(sentence)` for bytes, followed by
`sys.stdout.buffer.flush()`.

**Warning signs:** `--dry-run` output looks correct visually (terminals eat CR), but
`cat --show-all` or `xxd` shows `\n` only instead of `\r\n`.

### Pitfall 2: logging.basicConfig at module level

**What goes wrong:** Calling `logging.basicConfig(level=logging.INFO)` at the top of the
file (outside any function) bakes INFO level in before `parse_args()` runs. When the user
passes `-v`, the root logger level is already fixed and DEBUG messages are silently
dropped.

**Why it happens:** `basicConfig` is a one-shot configuration: the first call wins.
Subsequent calls are ignored unless `force=True` (Python 3.8+, but use `force=True`
sparingly — it also resets existing handlers).

**How to avoid:** Call `setup_logging(args.verbose)` from `main()` after `parse_args()`
returns.

**Warning signs:** `-v` flag has no effect on output verbosity.

### Pitfall 3: Replacing the Phase 1 entry point incompletely

**What goes wrong:** The current `if __name__ == '__main__':` block uses a bare
`if '--self-test' in sys.argv:` check. If this is deleted and replaced by argparse, but
`run_self_test()` is not wired to `args.self_test`, the `--self-test` flag silently does
nothing (no error, just falls through to the main loop).

**Why it happens:** argparse validates flags but does not route execution. The routing is
always manual `if args.self_test: run_self_test()` code.

**How to avoid:** The entry point must check `args.self_test` explicitly before entering
the main loop. The existing Phase 1 tests (`test_self_test_exits_zero_all_pass` etc.)
will catch this immediately — run `pytest tests/` after wiring argparse.

**Warning signs:** `python3 nixichron_gps.py --self-test` starts printing sentences
instead of running the test.

### Pitfall 4: Forgetting args.dry_run attribute name

**What goes wrong:** Referencing `args.dry-run` (hyphen) causes `AttributeError`. The
correct attribute is `args.dry_run` (underscore).

**Why it happens:** argparse silently converts hyphens to underscores in `dest`.

**How to avoid:** Always use underscore in code (`args.dry_run`, `args.self_test`).
Verified locally: `parse_args([])` returns `Namespace(dry_run=False, self_test=False)`.

### Pitfall 5: run_self_test output goes to logging instead of print

**What goes wrong:** If `run_self_test()` is refactored to use `logger.info()` instead
of `print()`, the output format becomes `HH:MM:SS INFO $GPRMC,...  PASS`, which is
verbose and ugly. More importantly, the subprocess tests capture `stdout` — log output
goes to `stderr` by default with the standard StreamHandler, so
`test_self_test_prints_exactly_5_lines` would fail (0 lines in stdout).

**Why it happens:** `logging.basicConfig` by default adds a `StreamHandler` to `stderr`.

**How to avoid:** Keep `print()` in `run_self_test()`. This is the one correct exception
to LOG-03: self-test output is a human-readable pass/fail report, not a runtime log event.

## Code Examples

Verified patterns from confirmed testing:

### Complete parse_args() function

```python
# Source: verified locally with python3 -c "..." — Python 3.9.6 confirmed
import argparse
import os

def parse_args():
    default_port = os.environ.get('GPS_PORT', '/dev/ttyUSB0')
    parser = argparse.ArgumentParser(
        description='NixiChron GPS Emulator — feeds $GPRMC sentences to a Nixie tube clock',
    )
    parser.add_argument(
        '--port',
        default=default_port,
        metavar='DEVICE',
        help='Serial port (default: GPS_PORT env or /dev/ttyUSB0)',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print sentences to stdout; do not open serial port',
    )
    parser.add_argument(
        '--self-test',
        action='store_true',
        help='Generate 5 sentences, verify checksums, exit 0/1',
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Set log level to DEBUG (default: INFO)',
    )
    return parser.parse_args()
```

### setup_logging() function

```python
# Source: Python 3.9 stdlib logging docs — verified locally
import logging

logger = logging.getLogger('nixichron')

def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
    )
```

### main() stub (Phase 2 version)

```python
# Source: patterns verified locally; Phase 3-5 will extend this
import sys
import time
from datetime import datetime, timezone

def main() -> None:
    args = parse_args()
    setup_logging(args.verbose)

    if args.self_test:
        run_self_test()  # exits 0 or 1 — never returns

    while True:
        utc_dt = datetime.now(timezone.utc)
        sentence = build_gprmc(utc_dt)
        logger.debug(sentence.decode('ascii').strip())  # LOG-01

        if args.dry_run:
            sys.stdout.buffer.write(sentence)
            sys.stdout.buffer.flush()
        else:
            # Phase 5 opens serial port and writes here
            pass

        time.sleep(1)  # Phase 3 replaces with deadline-based sleep


if __name__ == '__main__':
    main()
```

### Verifying CRLF preservation in dry-run output

```bash
# Confirm sentence bytes contain \r\n (not just \n):
python3 src/nixichron_gps.py --dry-run | xxd | head -2
# Should show 0d 0a at end of each 68-byte sentence line
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `if '--self-test' in sys.argv` | `argparse.ArgumentParser` | Phase 2 | Proper flag help, `-h` support, attribute access |
| `print(sentence.decode())` | `sys.stdout.buffer.write(sentence)` | Phase 2 | Preserves exact `\r\n` bytes in dry-run output |

**Deprecated/outdated:**
- Bare `sys.argv` check from Phase 1: replaced by `parse_args()` in Phase 2. The
  subprocess-based Phase 1 tests still pass because `--self-test` now routes through
  `args.self_test` which calls the same `run_self_test()`.

## Open Questions

1. **Should `--dry-run` loop run indefinitely or for a fixed count?**
   - What we know: Phase 2 success criterion says "prints valid sentences to stdout."
     VAL-02 says "for 5 seconds." Phase 3 adds the proper timing loop.
   - What's unclear: Whether Phase 2's loop should be naive infinite (Ctrl-C to stop)
     or emit a fixed N sentences and exit cleanly.
   - Recommendation: Infinite loop with `time.sleep(1)` placeholder. The user Ctrl-Cs
     to stop. Phase 4 adds the clean SIGINT handler. Phase 3 replaces the sleep.

2. **Should the `logger` be module-level or created inside `setup_logging`?**
   - What we know: Module-level `logger = logging.getLogger('nixichron')` is the
     conventional Python pattern. It is safe to call before `basicConfig` — messages
     are buffered in the logger until a handler is attached.
   - Recommendation: Module-level `logger = logging.getLogger('nixichron')` just below
     the imports. `setup_logging()` calls `basicConfig`, which attaches the handler.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.9+ | Runtime | Yes | 3.9.6 | — |
| `argparse` | CLI-01..04 | Yes | stdlib | — |
| `logging` | LOG-01..03 | Yes | stdlib | — |
| `os` | CLI-01 (GPS_PORT) | Yes | stdlib | — |
| `sys` | CLI-02 (dry-run) | Yes | stdlib | — |
| `time` | CLI-02 (sleep loop) | Yes | stdlib | — |
| `pytest` | Test framework | Yes | 8.4.2 | — |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | none — rootdir auto-detected as `/Users/jdonalds/Projects/newnixie` |
| Quick run command | `python3 -m pytest tests/ -q` |
| Full suite command | `python3 -m pytest tests/ -v` |

### Phase Requirements to Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `--port /dev/foo` stores port in args | unit | `pytest tests/test_cli.py::test_port_arg -x` | No — Wave 0 |
| CLI-01 | `GPS_PORT` env var used when `--port` absent | unit | `pytest tests/test_cli.py::test_gps_port_env -x` | No — Wave 0 |
| CLI-01 | Default port is `/dev/ttyUSB0` when neither set | unit | `pytest tests/test_cli.py::test_port_default -x` | No — Wave 0 |
| CLI-02 | `--dry-run` prints sentences to stdout | subprocess | `pytest tests/test_cli.py::test_dry_run_output -x` | No — Wave 0 |
| CLI-02 | `--dry-run` output contains valid `$GPRMC` sentences | subprocess | `pytest tests/test_cli.py::test_dry_run_gprmc_format -x` | No — Wave 0 |
| CLI-02 | `--dry-run` output sentences have valid checksums | subprocess | `pytest tests/test_cli.py::test_dry_run_checksums -x` | No — Wave 0 |
| CLI-03 | `--self-test` still exits 0 and prints PASS after argparse refactor | subprocess | `pytest tests/test_verify_and_self_test.py -x` | Yes — existing |
| CLI-04 | `-v` flag causes DEBUG lines to appear in stderr | subprocess | `pytest tests/test_cli.py::test_verbose_flag -x` | No — Wave 0 |
| CLI-04 | Without `-v`, DEBUG lines are absent | subprocess | `pytest tests/test_cli.py::test_no_verbose_no_debug -x` | No — Wave 0 |
| LOG-01 | Sentence logged at DEBUG when dry-run runs with -v | subprocess | `pytest tests/test_cli.py::test_sentence_debug_logged -x` | No — Wave 0 |
| LOG-03 | No bare print() in main loop dispatch path | static/code review | Manual inspection of `if __name__ == '__main__'` block | No |

### Sampling Rate

- **Per task commit:** `python3 -m pytest tests/ -q`
- **Per wave merge:** `python3 -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cli.py` — covers CLI-01, CLI-02, CLI-04, LOG-01 (11 new tests)
- [ ] No framework install needed — pytest 8.4.2 already present

## Project Constraints (from CLAUDE.md)

These directives apply to Phase 2 implementation:

- **Never save to root folder** — test file goes to `/tests/test_cli.py`, source stays in `/src/nixichron_gps.py`
- **Keep files under 500 lines** — `nixichron_gps.py` is currently 115 lines; Phase 2 adds ~60 lines (well under limit)
- **Use typed interfaces for all public APIs** — `parse_args() -> argparse.Namespace`, `setup_logging(verbose: bool) -> None`, `main() -> None`
- **ALWAYS read a file before editing it** — must read `nixichron_gps.py` before writing Phase 2 additions
- **ALWAYS run tests after making code changes** — run `python3 -m pytest tests/ -q` after each task
- **NEVER commit secrets, credentials, or .env files** — not applicable (no secrets in this phase)
- **TDD London School (mock-first)** — write `tests/test_cli.py` tests first (RED), then implement, then GREEN

**CLAUDE.md note:** The `npm run build` / `npm test` / `npm run lint` commands in CLAUDE.md are for a different project configuration. This project uses `python3 -m pytest tests/` as the test command. The Python constraints override the npm references.

## Sources

### Primary (HIGH confidence)

- Python 3.9 argparse docs (stdlib) — `ArgumentParser`, `add_argument`, `action='store_true'`, `default=`, hyphen-to-underscore dest conversion
- Python 3.9 logging docs (stdlib) — `basicConfig`, `getLogger`, `DEBUG`/`INFO`/`ERROR` levels, `StreamHandler`
- Python 3.9 sys docs (stdlib) — `sys.stdout.buffer` binary stream
- Python 3.9 os docs (stdlib) — `os.environ.get(key, default)`
- Local verification (`python3 -c "..."`) — argparse dest naming, logging output format, stdout.buffer CRLF preservation confirmed on Python 3.9.6

### Secondary (MEDIUM confidence)

- Existing Phase 1 test suite (`tests/test_verify_and_self_test.py`) — 12 tests all passing; Phase 2 must not break them
- Project RESEARCH SUMMARY (`.planning/research/SUMMARY.md`) — architecture layer model, logging approach, argparse recommendation

### Tertiary (LOW confidence)

- None — all claims in this research are directly verifiable via stdlib docs or local execution.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, verified locally on Python 3.9.6
- Architecture: HIGH — direct continuation of established Phase 1 layer model
- Pitfalls: HIGH — most verified empirically (`python3 -c` tests confirmed attribute naming, buffer behavior, basicConfig timing)

**Research date:** 2026-04-09
**Valid until:** 2027-04-09 (argparse and logging APIs are stable; no volatility expected)
