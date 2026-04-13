"""Tests for Phase 2 CLI shell and logging (CLI-01..04, LOG-01).

Group A: Unit tests for parse_args() — import directly from module.
Group B: Subprocess integration tests for --dry-run and -v behavior.

All Group A tests will FAIL (RED) until Plan 02 adds parse_args().
All Group B tests will FAIL (RED) until Plan 02 adds main() with dispatch.
"""

import sys
import signal
import subprocess
import importlib
import importlib.util

# Project root is two levels up from tests/
import pathlib
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / 'src' / 'nixichron_gps.py'

# ---------------------------------------------------------------------------
# Helper: import parse_args from the source file directly (not as a package)
# ---------------------------------------------------------------------------

def _load_module():
    """Load nixichron_gps as a module without executing __main__ block."""
    spec = importlib.util.spec_from_file_location('nixichron_gps', SRC_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Group A: parse_args() unit tests (CLI-01, CLI-02, CLI-03, CLI-04)
# ---------------------------------------------------------------------------

class TestParseArgs:

    def test_port_arg(self):
        """CLI-01: --port /dev/foo stores that path in args.port."""
        mod = _load_module()
        args = mod.parse_args(['--port', '/dev/foo'])
        assert args.port == '/dev/foo'

    def test_gps_port_env(self, monkeypatch):
        """CLI-01: GPS_PORT env var is used when --port is absent."""
        monkeypatch.setenv('GPS_PORT', '/dev/bar')
        mod = _load_module()
        args = mod.parse_args([])
        assert args.port == '/dev/bar'

    def test_port_default(self, monkeypatch):
        """CLI-01: Default port is autodetected when neither --port nor GPS_PORT set."""
        monkeypatch.delenv('GPS_PORT', raising=False)
        mod = _load_module()
        args = mod.parse_args([])
        # Autodetect returns a real port or /dev/ttyUSB0 fallback — just verify it's a string
        assert isinstance(args.port, str)
        assert args.port.startswith('/dev/')

    def test_dry_run_flag(self):
        """CLI-02: --dry-run sets args.dry_run to True."""
        mod = _load_module()
        args = mod.parse_args(['--dry-run'])
        assert args.dry_run is True

    def test_self_test_flag(self):
        """CLI-03: --self-test sets args.self_test to True."""
        mod = _load_module()
        args = mod.parse_args(['--self-test'])
        assert args.self_test is True

    def test_verbose_flag_long(self):
        """CLI-04: --verbose sets args.verbose to True."""
        mod = _load_module()
        args = mod.parse_args(['--verbose'])
        assert args.verbose is True

    def test_verbose_flag_short(self):
        """CLI-04: -v sets args.verbose to True (short form)."""
        mod = _load_module()
        args = mod.parse_args(['-v'])
        assert args.verbose is True


# ---------------------------------------------------------------------------
# Group B: Subprocess integration tests (CLI-02, CLI-04, LOG-01)
# ---------------------------------------------------------------------------

def _run_dry_run(extra_args=None, timeout=3):
    """Run --dry-run for ~2 seconds, return (stdout_bytes, stderr_bytes).

    Uses Popen + communicate(timeout=) to capture output then terminate.
    """
    cmd = [sys.executable, str(SRC_PATH), '--dry-run'] + (extra_args or [])
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate()
    return stdout, stderr


class TestDryRunOutput:

    def test_dry_run_output(self):
        """CLI-02: --dry-run prints at least one $GPRMC line to stdout."""
        stdout, _ = _run_dry_run()
        lines = [ln for ln in stdout.split(b'\r\n') if ln]
        assert any(line.startswith(b'$GPRMC') for line in lines), (
            f'No $GPRMC line found in stdout. Got: {stdout[:200]!r}'
        )

    def test_dry_run_gprmc_format(self):
        """CLI-02: First $GPRMC sentence has exactly 13 fields and ends with CRLF."""
        stdout, _ = _run_dry_run()
        # Find first complete sentence (ends with CRLF)
        sentences = [s + b'\r\n' for s in stdout.split(b'\r\n') if s.startswith(b'$GPRMC')]
        assert sentences, 'No complete $GPRMC sentence found'
        first = sentences[0]
        assert first.endswith(b'\r\n'), 'Sentence does not end with CRLF'
        # Strip $, *, checksum, CRLF — count fields
        body = first.decode('ascii').strip()
        # $GPRMC,f1,f2,...,f11,f12*HH  → split on comma gives 13 parts (field 0 = $GPRMC)
        parts = body.split('*')[0].split(',')
        assert len(parts) == 13, f'Expected 13 fields, got {len(parts)}: {parts}'

    def test_dry_run_checksums(self):
        """CLI-02 + VAL-02: All captured $GPRMC sentences have valid checksums."""
        spec = importlib.util.spec_from_file_location('nixichron_gps', SRC_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        stdout, _ = _run_dry_run()
        sentences = [s + b'\r\n' for s in stdout.split(b'\r\n') if s.startswith(b'$GPRMC')]
        assert sentences, 'No sentences captured'
        for sentence in sentences:
            assert mod.verify_gprmc_checksum(sentence), (
                f'Invalid checksum in: {sentence!r}'
            )


class TestVerboseLogging:

    def test_verbose_debug_in_stderr(self):
        """CLI-04 + LOG-01: -v flag causes DEBUG sentences to appear in stderr."""
        _, stderr = _run_dry_run(extra_args=['-v'])
        assert b'DEBUG' in stderr, (
            f'Expected DEBUG in stderr with -v. Got stderr: {stderr[:300]!r}'
        )

    def test_no_verbose_no_debug(self):
        """CLI-04: Without -v, DEBUG lines are absent from stderr."""
        _, stderr = _run_dry_run()
        assert b'DEBUG' not in stderr, (
            f'Expected no DEBUG in stderr without -v. Got: {stderr[:300]!r}'
        )
