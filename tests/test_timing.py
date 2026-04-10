"""Tests for Phase 3 timing loop (TIME-01, TIME-02, TIME-03).

Tests sleep_until_next_second() deadline-based helper and verifies the
main() loop captures datetime AFTER sleeping to the second boundary.

TestSleepUntilNextSecond: 4 unit tests (mocked — no real waits)
TestLoopOrder: 1 structural test (source inspection)
TestTimingIntegration: 1 integration test (~12 seconds real time)
"""

import os
import sys
import signal
import subprocess
import importlib
import importlib.util
import pathlib
import re
import inspect
import pytest
from unittest.mock import patch
from datetime import datetime

# Project root is two levels up from tests/
PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / 'src' / 'nixichron_gps.py'


# ---------------------------------------------------------------------------
# Helper: import nixichron_gps from the source file directly (no sys.path pollution)
# ---------------------------------------------------------------------------

def _load_module():
    """Load nixichron_gps as a module without executing __main__ block.

    Registers the module in sys.modules under 'nixichron_gps' so that
    unittest.mock.patch('nixichron_gps.time.time', ...) can resolve the target.
    """
    spec = importlib.util.spec_from_file_location('nixichron_gps', SRC_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['nixichron_gps'] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# Unit tests for sleep_until_next_second() (TIME-02)
# ---------------------------------------------------------------------------

class TestSleepUntilNextSecond:

    def test_sleeps_fractional_complement(self):
        """TIME-02: At t=1234.750, must sleep ~0.250 seconds (next boundary minus now)."""
        mod = _load_module()
        with patch('nixichron_gps.time.time', return_value=1234.750), \
             patch('nixichron_gps.time.sleep') as mock_sleep:
            mod.sleep_until_next_second()
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert abs(sleep_arg - 0.250) < 1e-6, (
            f'Expected ~0.250, got {sleep_arg}'
        )

    def test_sleeps_zero_at_exact_boundary(self):
        """TIME-02: At t=1234.0 (exact integer), sleep arg must be >= 0.0 (no negative)."""
        mod = _load_module()
        with patch('nixichron_gps.time.time', return_value=1234.0), \
             patch('nixichron_gps.time.sleep') as mock_sleep:
            mod.sleep_until_next_second()
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert sleep_arg >= 0.0, f'sleep arg must not be negative, got {sleep_arg}'

    def test_sleeps_near_zero_at_999ms(self):
        """TIME-02: At t=1234.999, sleep is < 0.001 and >= 0.0 (tiny remainder)."""
        mod = _load_module()
        with patch('nixichron_gps.time.time', return_value=1234.999), \
             patch('nixichron_gps.time.sleep') as mock_sleep:
            mod.sleep_until_next_second()
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert sleep_arg < 0.001, f'Expected < 0.001, got {sleep_arg}'
        assert sleep_arg >= 0.0, f'sleep arg must not be negative, got {sleep_arg}'

    def test_max_guard_prevents_negative(self):
        """TIME-02: If time.time() overshoots the tick (rare race), clamp to 0.0."""
        mod = _load_module()
        # First call returns a value just before the boundary, second call would
        # simulate overshooting — but sleep_until_next_second() calls time.time()
        # once and uses math.ceil. Simulate: now=1234.9999999, next_tick=1235,
        # sleep_arg = 1235 - 1234.9999999 = ~1e-7 (positive, not negative here).
        # For a true race (where subtraction yields tiny negative due to FP), we
        # simulate by making time.time() return a value where math.ceil(now) - now
        # is negative (impossible mathematically but can occur due to FP precision).
        # We patch math.ceil to return a value less than now to force the clamp.
        with patch('nixichron_gps.time.time', return_value=1234.9999999), \
             patch('nixichron_gps.math.ceil', return_value=1234) as _mock_ceil, \
             patch('nixichron_gps.time.sleep') as mock_sleep:
            mod.sleep_until_next_second()
        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert sleep_arg == 0.0, (
            f'max guard must clamp negative to 0.0, got {sleep_arg}'
        )


# ---------------------------------------------------------------------------
# Structural test for loop ordering in main() (TIME-03)
# ---------------------------------------------------------------------------

class TestLoopOrder:

    def test_timestamp_captured_after_sleep(self):
        """TIME-03: In main(), sleep_until_next_second() appears before datetime.now().

        Uses source inspection — a structural guarantee that the loop order is correct.
        This catches any accidental reordering of the two calls in main().
        """
        mod = _load_module()
        source = inspect.getsource(mod.main)
        sleep_pos = source.find('sleep_until_next_second()')
        datetime_pos = source.find('datetime.now(')
        assert sleep_pos != -1, (
            'sleep_until_next_second() not found in main() source'
        )
        assert datetime_pos != -1, (
            'datetime.now( not found in main() source'
        )
        assert sleep_pos < datetime_pos, (
            f'sleep_until_next_second() (pos {sleep_pos}) must appear before '
            f'datetime.now( (pos {datetime_pos}) in main() source'
        )


# ---------------------------------------------------------------------------
# Integration test: 1 Hz loop produces advancing timestamps (TIME-01, TIME-03)
# ---------------------------------------------------------------------------

class TestTimingIntegration:

    def test_timestamps_advance_by_one_second(self):
        """TIME-01: --dry-run for ~12s produces >= 10 sentences with timestamps 1 s apart.

        Spawns subprocess, collects output for 12 seconds, sends SIGTERM, parses
        $GPRMC time fields, asserts 1-second step between every consecutive pair.
        Handles midnight rollover via mod 86400.
        """
        cmd = [sys.executable, str(SRC_PATH), '--dry-run']
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            stdout, _ = proc.communicate(timeout=12)
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGTERM)
            stdout, _ = proc.communicate()

        # Parse $GPRMC lines and extract hhmmss time field (field index 1)
        lines = [l for l in stdout.split(b'\r\n') if l.startswith(b'$GPRMC')]
        assert len(lines) >= 10, (
            f'Expected >= 10 $GPRMC sentences, got {len(lines)}'
        )

        # Extract hhmmss as total seconds since midnight
        def hhmmss_to_seconds(field):
            h = int(field[0:2])
            m = int(field[2:4])
            s = int(field[4:6])
            return h * 3600 + m * 60 + s

        timestamps = []
        for line in lines:
            decoded = line.decode('ascii').strip()
            fields = decoded.split(',')
            if len(fields) >= 2:
                time_field = fields[1][:6]  # hhmmss (ignore .00 subseconds)
                if re.match(r'^\d{6}$', time_field):
                    timestamps.append(hhmmss_to_seconds(time_field))

        assert len(timestamps) >= 10, (
            f'Could not parse >= 10 timestamps from output. Parsed: {timestamps}'
        )

        for i in range(1, len(timestamps)):
            diff = (timestamps[i] - timestamps[i - 1]) % 86400
            assert diff == 1, (
                f'Timestamp step at index {i} is {diff}s, expected 1s. '
                f'Timestamps: {timestamps[i-1]} -> {timestamps[i]}'
            )
