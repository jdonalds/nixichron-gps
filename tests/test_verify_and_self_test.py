"""TDD tests for verify_gprmc_checksum() and run_self_test() — Phase 01 Plan 02.

These tests are written BEFORE implementation (RED phase). They must fail
until verify_gprmc_checksum and run_self_test are added to nixichron_gps.py.
"""

import subprocess
import sys
import os
from datetime import datetime, timezone

# Add project src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest


def test_verify_gprmc_checksum_is_importable():
    """verify_gprmc_checksum must exist in nixichron_gps module."""
    from nixichron_gps import verify_gprmc_checksum
    assert callable(verify_gprmc_checksum)


def test_run_self_test_is_importable():
    """run_self_test must exist in nixichron_gps module."""
    from nixichron_gps import run_self_test
    assert callable(run_self_test)


def test_verify_gprmc_checksum_valid_sentence():
    """Returns True when embedded checksum matches computed XOR."""
    from nixichron_gps import build_gprmc, verify_gprmc_checksum
    utc_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    sentence_bytes = build_gprmc(utc_dt)
    assert verify_gprmc_checksum(sentence_bytes) is True


def test_verify_gprmc_checksum_wrong_checksum():
    """Returns False when the embedded checksum is 00 and that's wrong."""
    from nixichron_gps import build_gprmc, verify_gprmc_checksum
    utc_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    sentence_bytes = build_gprmc(utc_dt)
    # Corrupt checksum: replace last two chars before \r\n with 00
    sentence_str = sentence_bytes.decode('ascii')
    # Find the star and replace checksum with 00
    star_pos = sentence_str.index('*')
    corrupted = sentence_str[:star_pos + 1] + '00' + sentence_str[star_pos + 3:]
    assert verify_gprmc_checksum(corrupted.encode('ascii')) is False


def test_verify_gprmc_checksum_no_dollar():
    """Returns False for input that does not start with '$'."""
    from nixichron_gps import verify_gprmc_checksum
    assert verify_gprmc_checksum(b'GPRMC,120000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A*50\r\n') is False


def test_verify_gprmc_checksum_no_star():
    """Returns False for input with no '*'."""
    from nixichron_gps import verify_gprmc_checksum
    assert verify_gprmc_checksum(b'$GPRMC,120000.00,A,0000.0000,N,00000.0000,E,0.0,0.0,150126,,,A\r\n') is False


def test_verify_does_not_call_nmea_checksum():
    """verify_gprmc_checksum must be an independent XOR implementation.

    We monkey-patch nmea_checksum to raise an exception. If verify_gprmc_checksum
    calls it, this test will fail — catching any D-02 violation.
    """
    import nixichron_gps
    from nixichron_gps import build_gprmc, verify_gprmc_checksum

    original = nixichron_gps.nmea_checksum
    def forbidden(*args, **kwargs):
        raise AssertionError("verify_gprmc_checksum must not call nmea_checksum (D-02)")
    nixichron_gps.nmea_checksum = forbidden
    try:
        utc_dt = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        sentence_bytes = build_gprmc(utc_dt)
        # build_gprmc calls nmea_checksum — build first, THEN patch
        nixichron_gps.nmea_checksum = forbidden
        result = verify_gprmc_checksum(sentence_bytes)
        assert result is True
    finally:
        nixichron_gps.nmea_checksum = original


def test_self_test_exits_zero_all_pass():
    """python3 src/nixichron_gps.py --self-test exits with code 0."""
    script = os.path.join(os.path.dirname(__file__), '..', 'src', 'nixichron_gps.py')
    result = subprocess.run(
        [sys.executable, script, '--self-test'],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_self_test_prints_exactly_5_lines():
    """Self-test prints exactly 5 non-empty lines."""
    script = os.path.join(os.path.dirname(__file__), '..', 'src', 'nixichron_gps.py')
    result = subprocess.run(
        [sys.executable, script, '--self-test'],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) == 5, f"Expected 5 lines, got {len(lines)}: {result.stdout}"


def test_self_test_all_lines_end_in_pass():
    """Every line printed by --self-test ends in PASS."""
    script = os.path.join(os.path.dirname(__file__), '..', 'src', 'nixichron_gps.py')
    result = subprocess.run(
        [sys.executable, script, '--self-test'],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    for line in lines:
        assert line.endswith('PASS'), f"Line does not end in PASS: {repr(line)}"


def test_self_test_no_fail_lines():
    """--self-test output contains no FAIL lines."""
    script = os.path.join(os.path.dirname(__file__), '..', 'src', 'nixichron_gps.py')
    result = subprocess.run(
        [sys.executable, script, '--self-test'],
        capture_output=True, text=True
    )
    assert 'FAIL' not in result.stdout, f"Found FAIL in output:\n{result.stdout}"


def test_self_test_all_lines_start_with_gprmc():
    """Every sentence line starts with $GPRMC."""
    script = os.path.join(os.path.dirname(__file__), '..', 'src', 'nixichron_gps.py')
    result = subprocess.run(
        [sys.executable, script, '--self-test'],
        capture_output=True, text=True
    )
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    for line in lines:
        assert line.startswith('$GPRMC'), f"Line does not start with $GPRMC: {repr(line)}"
