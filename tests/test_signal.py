"""Tests for Phase 4 signal handling (SIG-01, SIG-02).

TestSignalHandling: subprocess integration tests — send SIGTERM/SIGINT, assert clean exit.
TestShutdownFlag: source inspection tests — assert structural patterns in main().
"""

import inspect
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

import pytest

# Project root is two levels up from tests/
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / 'src' / 'nixichron_gps.py'


# ---------------------------------------------------------------------------
# Class 1: Subprocess integration tests for signal handling (SIG-01)
# ---------------------------------------------------------------------------

class TestSignalHandling:

    def test_sigterm_clean_exit(self):
        """SIG-01: SIGTERM causes a clean exit — returncode 0, no traceback."""
        proc = subprocess.Popen(
            [sys.executable, str(SRC_PATH), '--dry-run'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for loop to start: read chunks until a $GPRMC line is received
        deadline = time.time() + 5.0
        started = False
        buf = b''
        while time.time() < deadline:
            chunk = proc.stdout.read(64)
            if not chunk:
                break
            buf += chunk
            if b'$GPRMC' in buf:
                started = True
                break
        if not started:
            proc.kill()
            proc.communicate()
            pytest.fail('process never started loop — no $GPRMC output within 5 seconds')

        proc.send_signal(signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=5)
        assert proc.returncode == 0, (
            f'Expected returncode 0 after SIGTERM, got {proc.returncode}. '
            f'stderr: {stderr[:300]!r}'
        )
        assert b'Traceback' not in stderr, (
            f'Unexpected traceback in stderr after SIGTERM: {stderr[:300]!r}'
        )

    def test_sigint_clean_exit(self):
        """SIG-01: SIGINT causes a clean exit — returncode 0, no traceback."""
        proc = subprocess.Popen(
            [sys.executable, str(SRC_PATH), '--dry-run'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for loop to start: read chunks until a $GPRMC line is received
        deadline = time.time() + 5.0
        started = False
        buf = b''
        while time.time() < deadline:
            chunk = proc.stdout.read(64)
            if not chunk:
                break
            buf += chunk
            if b'$GPRMC' in buf:
                started = True
                break
        if not started:
            proc.kill()
            proc.communicate()
            pytest.fail('process never started loop — no $GPRMC output within 5 seconds')

        proc.send_signal(signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=5)
        assert proc.returncode == 0, (
            f'Expected returncode 0 after SIGINT, got {proc.returncode}. '
            f'stderr: {stderr[:300]!r}'
        )
        assert b'Traceback' not in stderr, (
            f'Unexpected traceback in stderr after SIGINT: {stderr[:300]!r}'
        )


# ---------------------------------------------------------------------------
# Class 2: Source inspection tests for shutdown flag and try/finally (SIG-02)
# ---------------------------------------------------------------------------

class TestShutdownFlag:

    def test_loop_uses_shutdown_flag(self):
        """SIG-02: main() must poll _shutdown flag, not use 'while True'."""
        source = SRC_PATH.read_text()
        assert 'while not _shutdown' in source, (
            "main() must poll _shutdown flag, not use 'while True'"
        )

    def test_finally_block_present(self):
        """SIG-02: main() must have try/finally for port cleanup."""
        source = SRC_PATH.read_text()
        match = re.search(r'try:[\s\S]+?finally:', source, re.DOTALL)
        assert match is not None, (
            "main() must have try/finally for port cleanup (SIG-02)"
        )
