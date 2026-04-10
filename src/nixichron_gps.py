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
import math
import os
import serial
import signal
import sys
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger('nixichron')

# ---------------------------------------------------------------------------
# Layer 0: Signal handling (SIG-01, SIG-02)
# ---------------------------------------------------------------------------

_shutdown = False


def _handle_signal(signum, frame) -> None:
    """Set _shutdown flag on SIGTERM or SIGINT. No I/O, no cleanup here."""
    global _shutdown
    _shutdown = True


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
# Layer 4: Logging setup (LOG-01, LOG-02, LOG-03)
# ---------------------------------------------------------------------------

def setup_logging(verbose: bool) -> None:
    """Configure root logger from main() — not at module level.

    basicConfig is one-shot; calling at module level bakes INFO before --verbose is parsed.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%H:%M:%S',
    )


# ---------------------------------------------------------------------------
# Layer 5: Deadline-based timing (TIME-02, TIME-03)
# ---------------------------------------------------------------------------

def sleep_until_next_second() -> None:
    """Sleep until the start of the next UTC second boundary.

    Deadline-based: computes next integer second from wall clock, sleeps the
    fractional remainder. Self-correcting per iteration — no drift accumulation.
    The max(0.0, ...) guard prevents ValueError if called at an exact second
    boundary where floating-point arithmetic produces a tiny negative value.
    """
    now = time.time()
    next_tick = math.ceil(now)
    time.sleep(max(0.0, next_tick - now))


# ---------------------------------------------------------------------------
# Layer 5b: Serial port helper (SER-01)
# ---------------------------------------------------------------------------

def open_serial(port: str) -> "serial.Serial":
    """Open serial port at 4800/8N1, no flow control.

    Raises serial.SerialException if port cannot be opened.
    write_timeout=2 prevents indefinite blocking on stall (pyserial issue #281).
    dsrdtr/rtscts/xonxoff all False — NixiChron is TX-only, no handshaking.
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


# ---------------------------------------------------------------------------
# Layer 6: Argument parser (CLI-01, CLI-02, CLI-03, CLI-04)
# ---------------------------------------------------------------------------

def parse_args(args=None) -> argparse.Namespace:
    """Parse CLI arguments. args=None uses sys.argv; pass list for unit tests.

    Port: --port > GPS_PORT env > /dev/ttyUSB0 default.
    """
    default_port = os.environ.get('GPS_PORT', '/dev/ttyUSB0')
    parser = argparse.ArgumentParser(
        description='NixiChron GPS Emulator — feeds $GPRMC sentences to a Nixie tube clock',
    )
    parser.add_argument(
        '--port',
        default=default_port,
        metavar='DEVICE',
        help='Serial port device (default: GPS_PORT env or /dev/ttyUSB0)',
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
    return parser.parse_args(args)


# ---------------------------------------------------------------------------
# Layer 7: Main dispatch (Phase 3 adds deadline timing, Phase 5 adds serial)
# ---------------------------------------------------------------------------

def main() -> None:
    """Entry point. parse_args -> setup_logging -> self_test or dry-run loop.

    sys.stdout.buffer.write preserves exact \\r\\n bytes (not sys.stdout.write).
    Phase 3 replaces time.sleep(1); Phase 5 adds serial write.
    """
    args = parse_args()
    setup_logging(args.verbose)

    if args.self_test:
        run_self_test()  # exits 0 or 1 — never returns here

    # Register handlers inside main() — not at module level (avoids firing during --self-test)
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    port = None
    _BACKOFF_BASE = 1.0
    _BACKOFF_MAX = 30.0
    _delay = _BACKOFF_BASE
    try:
        while not _shutdown:
            sleep_until_next_second()
            utc_dt = datetime.now(timezone.utc)
            sentence = build_gprmc(utc_dt)
            logger.debug(sentence.decode('ascii').strip())  # LOG-01: sentence at DEBUG

            if args.dry_run:
                sys.stdout.buffer.write(sentence)  # preserves exact \r\n bytes
                sys.stdout.buffer.flush()
            else:
                # SER-01/02/03/04: serial write with exponential backoff reconnect
                if port is None:
                    while port is None and not _shutdown:
                        try:
                            port = open_serial(args.port)
                            logger.info('Serial port %s opened.', args.port)
                            _delay = _BACKOFF_BASE  # reset on success
                        except serial.SerialException as e:
                            logger.error('Cannot open %s: %s', args.port, e)
                            logger.warning('Retrying in %.0fs...', _delay)
                            time.sleep(_delay)
                            _delay = min(_delay * 2, _BACKOFF_MAX)
                if port is not None:
                    try:
                        port.write(sentence)
                    except serial.SerialException as e:
                        logger.error('Write error on %s: %s', args.port, e)
                        logger.warning('Port lost — reconnecting...')
                        _delay = _BACKOFF_BASE  # reset backoff for reconnect
                        time.sleep(_delay)       # brief pause before reconnect
                        try:
                            port.close()
                        except Exception:
                            pass
                        port = None  # triggers re-open on next iteration
    finally:
        if port is not None:
            port.close()
            logger.info('Serial port closed.')


if __name__ == '__main__':
    main()
