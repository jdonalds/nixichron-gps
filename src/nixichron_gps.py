"""NixiChron GPS Emulator — core sentence engine.

Phases 1-4 build on top of this file. Phase 1 adds:
  - nmea_checksum(): XOR checksum calculator (Layer 1)
  - build_gprmc(): $GPRMC sentence builder (Layer 2)
  - verify_gprmc_checksum(): independent verifier for self-test (Phase 1 Plan 02)
  - run_self_test(): self-test runner (Phase 1 Plan 02)

Phases 2-5 add CLI, timing loop, signal handling, and serial I/O below this block.
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger('nixichron')


# ---------------------------------------------------------------------------
# Layer 1: Checksum calculator (NMEA-02, D-01)
# ---------------------------------------------------------------------------

def nmea_checksum(sentence: str) -> str:
    """XOR all bytes between '$' and '*' (exclusive). Returns two uppercase hex digits.

    The input must contain both '$' and '*'. The checksum is computed over
    sentence[1:sentence.index('*')] — the '$' and '*' delimiters are excluded.
    """
    body = sentence[1:sentence.index('*')]
    checksum = 0
    for char in body:
        checksum ^= ord(char)
    return f'{checksum:02X}'


# ---------------------------------------------------------------------------
# Layer 2: Sentence builder (NMEA-01, NMEA-03..09, D-03..D-13)
# ---------------------------------------------------------------------------

def build_gprmc(utc_dt) -> bytes:
    """Build a complete $GPRMC sentence from a UTC datetime. Returns bytes with \\r\\n.

    The caller is responsible for capturing datetime.now(timezone.utc) and passing
    it in — this function has no side effects and does not read the clock (D-05).

    Locked format (D-11):
      $GPRMC,hhmmss.00,A,0000.0000,N,00000.0000,E,0.0,0.0,ddmmyy,,,A*HH\\r\\n

    Fields:
      0: hhmmss.00  1: A  2: 0000.0000  3: N  4: 00000.0000  5: E
      6: 0.0  7: 0.0  8: ddmmyy  9: (empty)  10: (empty)  11: A
    """
    time_str = utc_dt.strftime('%H%M%S') + '.00'
    date_str = utc_dt.strftime('%d%m%y')  # NMEA date is ddmmyy, NOT yymmdd
    body = f'GPRMC,{time_str},A,0000.0000,N,00000.0000,E,0.0,0.0,{date_str},,,A'
    checksum = nmea_checksum('$' + body + '*')
    sentence = f'${body}*{checksum}\r\n'
    return sentence.encode('ascii')


# ---------------------------------------------------------------------------
# Layer 3a: Independent verifier for self-test (D-02)
# ---------------------------------------------------------------------------

def verify_gprmc_checksum(sentence_bytes: bytes) -> bool:
    """Parse a complete $GPRMC sentence and verify its checksum independently.

    This is a second, distinct XOR implementation — not a call to nmea_checksum().
    Required by D-02 to catch off-by-one bugs in the builder's checksum range.
    """
    try:
        sentence = sentence_bytes.decode('ascii').strip()
    except (UnicodeDecodeError, AttributeError):
        return False
    if not sentence.startswith('$') or '*' not in sentence:
        return False
    star_pos = sentence.index('*')
    embedded = sentence[star_pos + 1:star_pos + 3]
    # Independent XOR — same algorithm as nmea_checksum, separate code path
    body = sentence[1:star_pos]
    computed = 0
    for char in body:
        computed ^= ord(char)
    expected = f'{computed:02X}'
    return embedded == expected


# ---------------------------------------------------------------------------
# Layer 3b: Self-test runner (VAL-01, D-06, D-07)
# ---------------------------------------------------------------------------

def run_self_test() -> None:
    """Generate 5 sentences, verify checksums, print PASS/FAIL, exit 0 or 1.

    Uses a fixed base datetime with 1-hour increments so digits in both the
    time and date fields vary across the 5 sentences.
    """
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


# ---------------------------------------------------------------------------
# Entry point (Phase 2 adds argparse; Phase 1 only wires --self-test)
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        run_self_test()
