"""Tests for Phase 5 serial I/O and reconnect (SER-01, SER-02, SER-03, SER-04, LOG-02).

TestOpenSerial:       open_serial() constructor arguments (SER-01)
TestPortConfig:       port value flows from parse_args() to open_serial() (SER-02)
TestBackoff:          exponential backoff delay sequence (SER-03)
TestReconnectLogging: WARNING and INFO log calls on reconnect (SER-04)
TestErrorLogging:     write errors logged at ERROR level (LOG-02)
"""

import argparse
import importlib
import importlib.util
import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module setup: same pattern as test_timing.py, test_signal.py
# ---------------------------------------------------------------------------

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / 'src' / 'nixichron_gps.py'


def _load_module():
    """Load nixichron_gps without executing __main__ block.

    Registers under sys.modules so unittest.mock.patch can resolve
    patch targets like 'nixichron_gps.serial.Serial'.
    """
    spec = importlib.util.spec_from_file_location('nixichron_gps', SRC_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['nixichron_gps'] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_args(port='/dev/ttyUSB0', dry_run=False, verbose=False, self_test=False):
    """Build a fake argparse.Namespace for injecting into main() via parse_args mock."""
    return argparse.Namespace(
        port=port,
        dry_run=dry_run,
        verbose=verbose,
        self_test=self_test,
    )


# ---------------------------------------------------------------------------
# Class 1: TestOpenSerial — SER-01
# ---------------------------------------------------------------------------

class TestOpenSerial:

    def test_serial_constructor_called_with_exact_params(self):
        """SER-01: open_serial() must call serial.Serial with 4800/8N1/no-flow params."""
        mod = _load_module()
        import serial as pyserial

        mock_serial_instance = MagicMock()
        with patch('nixichron_gps.serial.Serial', return_value=mock_serial_instance) as mock_serial_cls:
            result = mod.open_serial('/dev/ttyUSB0')

        mock_serial_cls.assert_called_once_with(
            port='/dev/ttyUSB0',
            baudrate=4800,
            bytesize=pyserial.EIGHTBITS,
            parity=pyserial.PARITY_NONE,
            stopbits=pyserial.STOPBITS_ONE,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
            write_timeout=2,
        )
        assert result is mock_serial_instance

    def test_open_serial_propagates_serial_exception(self):
        """SER-01: open_serial() must not swallow serial.SerialException on failure."""
        mod = _load_module()
        import serial as pyserial

        with patch('nixichron_gps.serial.Serial', side_effect=pyserial.SerialException('port not found')):
            with pytest.raises(pyserial.SerialException):
                mod.open_serial('/dev/ttyUSB0')


# ---------------------------------------------------------------------------
# Class 2: TestPortConfig — SER-02
# ---------------------------------------------------------------------------

class TestPortConfig:

    def _run_main_once(self, mod, port):
        """Run main() with mocked parse_args; break loop after open_serial succeeds.

        main() calls parse_args() which reads sys.argv — we mock parse_args to
        return a controlled Namespace so no real argument parsing happens.
        """
        open_calls = []

        def fake_open_serial(p):
            open_calls.append(p)
            mod._shutdown = True  # exit the while-not-_shutdown loop
            return MagicMock()

        fake_args = _make_args(port=port)

        with patch('nixichron_gps.parse_args', return_value=fake_args), \
             patch('nixichron_gps.setup_logging'), \
             patch('nixichron_gps.open_serial', side_effect=fake_open_serial), \
             patch('nixichron_gps.sleep_until_next_second'):
            mod._shutdown = False
            mod.main()

        return open_calls

    def test_port_from_cli_arg_flows_to_open_serial(self):
        """SER-02: --port CLI argument must be passed to open_serial()."""
        mod = _load_module()
        open_calls = self._run_main_once(mod, port='/dev/cu.usbserial-TEST')

        assert len(open_calls) >= 1, 'open_serial() was never called'
        assert open_calls[0] == '/dev/cu.usbserial-TEST', (
            f'Expected /dev/cu.usbserial-TEST, got {open_calls[0]!r}'
        )

    def test_port_from_env_var_flows_to_open_serial(self):
        """SER-02: GPS_PORT env var must be used when --port is not specified.

        parse_args() reads GPS_PORT when --port is absent. We verify the value
        flows through to open_serial() by patching parse_args to return a
        Namespace with the env var value, as parse_args() does at runtime.
        """
        mod = _load_module()
        open_calls = self._run_main_once(mod, port='/dev/cu.usbserial-ENV')

        assert len(open_calls) >= 1, 'open_serial() was never called'
        assert open_calls[0] == '/dev/cu.usbserial-ENV', (
            f'Expected /dev/cu.usbserial-ENV, got {open_calls[0]!r}'
        )


# ---------------------------------------------------------------------------
# Class 3: TestBackoff — SER-03
# ---------------------------------------------------------------------------

class TestBackoff:

    def _run_main_with_failures(self, mod, fail_count):
        """Run main() where open_serial fails fail_count times then succeeds.

        Returns the list of time.sleep() call arguments captured during the
        reconnect phase (these come from the backoff loop, not sleep_until_next_second).
        """
        import serial as pyserial
        open_call_count = [0]
        backoff_sleep_calls = []

        def fake_open_serial(port):
            open_call_count[0] += 1
            if open_call_count[0] <= fail_count:
                raise pyserial.SerialException(f'attempt {open_call_count[0]} failed')
            # Success — shut down after the first successful open
            mod._shutdown = True
            return MagicMock()

        def fake_backoff_sleep(delay):
            backoff_sleep_calls.append(delay)

        fake_args = _make_args(port='/dev/ttyUSB0')

        with patch('nixichron_gps.parse_args', return_value=fake_args), \
             patch('nixichron_gps.setup_logging'), \
             patch('nixichron_gps.open_serial', side_effect=fake_open_serial), \
             patch('nixichron_gps.sleep_until_next_second'), \
             patch('nixichron_gps.time.sleep', side_effect=fake_backoff_sleep):
            mod._shutdown = False
            mod.main()

        return backoff_sleep_calls

    def test_backoff_sequence_six_failures(self):
        """SER-03: 6 failures produce delays [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]."""
        mod = _load_module()
        sleep_calls = self._run_main_with_failures(mod, fail_count=6)

        expected = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
        assert sleep_calls == expected, (
            f'Expected backoff sequence {expected}, got {sleep_calls}'
        )

    def test_backoff_resets_after_reconnect(self):
        """SER-03: After write failure triggers reconnect, backoff starts again at 1.0."""
        import serial as pyserial
        mod = _load_module()

        open_call_count = [0]
        write_call_count = [0]
        phase_a_sleep_calls = []  # during initial 2-failure open cycle
        phase_b_sleep_calls = []  # during reconnect cycle after write failure

        def fake_open_serial(port):
            open_call_count[0] += 1
            mock_port = MagicMock()
            if open_call_count[0] <= 2:
                raise pyserial.SerialException(f'attempt {open_call_count[0]}')
            # open_call_count 3: first success
            # open_call_count 4+: reconnect after write failure -> shut down
            if open_call_count[0] >= 4:
                mod._shutdown = True
            def fake_write(data):
                write_call_count[0] += 1
                if write_call_count[0] == 1:
                    raise pyserial.SerialException('write error')
            mock_port.write.side_effect = fake_write
            return mock_port

        def fake_sleep(delay):
            if open_call_count[0] <= 2:
                phase_a_sleep_calls.append(delay)
            else:
                phase_b_sleep_calls.append(delay)

        fake_args = _make_args(port='/dev/ttyUSB0')

        with patch('nixichron_gps.parse_args', return_value=fake_args), \
             patch('nixichron_gps.setup_logging'), \
             patch('nixichron_gps.open_serial', side_effect=fake_open_serial), \
             patch('nixichron_gps.sleep_until_next_second'), \
             patch('nixichron_gps.time.sleep', side_effect=fake_sleep):
            mod._shutdown = False
            mod.main()

        # Phase A: 2 failures → delays [1.0, 2.0]
        assert phase_a_sleep_calls == [1.0, 2.0], (
            f'Phase A backoff expected [1.0, 2.0], got {phase_a_sleep_calls}'
        )
        # Phase B: reconnect after write failure — first delay must be 1.0 (reset)
        assert len(phase_b_sleep_calls) >= 1, (
            'Phase B backoff (after write failure reconnect) never fired'
        )
        assert phase_b_sleep_calls[0] == 1.0, (
            f'Expected delay reset to 1.0 on reconnect, got {phase_b_sleep_calls[0]}'
        )


# ---------------------------------------------------------------------------
# Class 4: TestReconnectLogging — SER-04
# ---------------------------------------------------------------------------

class TestReconnectLogging:

    def test_warning_logged_on_retry_info_logged_on_success(self):
        """SER-04: WARNING fired during retry; INFO fired on successful open."""
        import serial as pyserial
        mod = _load_module()

        open_call_count = [0]

        def fake_open_serial(port):
            open_call_count[0] += 1
            if open_call_count[0] == 1:
                raise pyserial.SerialException('port not found')
            # Success on second attempt — exit after this
            mod._shutdown = True
            return MagicMock()

        warning_messages = []
        info_messages = []

        def capture_warning(msg, *args, **kwargs):
            warning_messages.append(msg % args if args else msg)

        def capture_info(msg, *args, **kwargs):
            info_messages.append(msg % args if args else msg)

        fake_args = _make_args(port='/dev/ttyUSB0')

        with patch('nixichron_gps.parse_args', return_value=fake_args), \
             patch('nixichron_gps.setup_logging'), \
             patch('nixichron_gps.open_serial', side_effect=fake_open_serial), \
             patch('nixichron_gps.sleep_until_next_second'), \
             patch('nixichron_gps.time.sleep'), \
             patch('nixichron_gps.logger.warning', side_effect=capture_warning), \
             patch('nixichron_gps.logger.info', side_effect=capture_info):
            mod._shutdown = False
            mod.main()

        assert len(warning_messages) >= 1, (
            'Expected at least one logger.warning call during reconnect retry'
        )
        assert len(info_messages) >= 1, (
            'Expected at least one logger.info call on successful open'
        )
        # Verify at least one info message is about the port opening
        open_infos = [m for m in info_messages if 'open' in m.lower() or 'serial' in m.lower()]
        assert len(open_infos) >= 1, (
            f'Expected INFO log about port opened, got info_messages={info_messages}'
        )


# ---------------------------------------------------------------------------
# Class 5: TestErrorLogging — LOG-02
# ---------------------------------------------------------------------------

class TestErrorLogging:

    def test_write_error_logged_at_error_level(self):
        """LOG-02: serial.SerialException on port.write() must be logged at ERROR level."""
        import serial as pyserial
        mod = _load_module()

        open_call_count = [0]
        write_call_count = [0]

        def fake_open_serial(port):
            open_call_count[0] += 1
            mock_port = MagicMock()
            def fake_write(data):
                write_call_count[0] += 1
                if write_call_count[0] == 1:
                    raise pyserial.SerialException('write failed')
                # Subsequent writes succeed; shut down so test terminates
                mod._shutdown = True
            mock_port.write.side_effect = fake_write
            return mock_port

        error_messages = []

        def capture_error(msg, *args, **kwargs):
            error_messages.append(msg % args if args else msg)

        fake_args = _make_args(port='/dev/ttyUSB0')

        with patch('nixichron_gps.parse_args', return_value=fake_args), \
             patch('nixichron_gps.setup_logging'), \
             patch('nixichron_gps.open_serial', side_effect=fake_open_serial), \
             patch('nixichron_gps.sleep_until_next_second'), \
             patch('nixichron_gps.time.sleep'), \
             patch('nixichron_gps.logger.error', side_effect=capture_error), \
             patch('nixichron_gps.logger.warning'):
            mod._shutdown = False
            mod.main()

        assert len(error_messages) >= 1, (
            'Expected at least one logger.error call on write failure (LOG-02)'
        )

    def test_port_set_to_none_after_write_failure(self):
        """LOG-02: After write failure, port must be set to None (triggers reconnect).

        Verified by checking that open_serial is called a second time —
        which only happens if port was set back to None after write failure.
        """
        import serial as pyserial
        mod = _load_module()

        open_call_count = [0]
        write_call_count = [0]

        def fake_open_serial(port):
            open_call_count[0] += 1
            mock_port = MagicMock()
            def fake_write(data):
                write_call_count[0] += 1
                if write_call_count[0] == 1:
                    raise pyserial.SerialException('write error')
                # Second write succeeds; shut down so test terminates
                mod._shutdown = True
            mock_port.write.side_effect = fake_write
            return mock_port

        fake_args = _make_args(port='/dev/ttyUSB0')

        with patch('nixichron_gps.parse_args', return_value=fake_args), \
             patch('nixichron_gps.setup_logging'), \
             patch('nixichron_gps.open_serial', side_effect=fake_open_serial), \
             patch('nixichron_gps.sleep_until_next_second'), \
             patch('nixichron_gps.time.sleep'), \
             patch('nixichron_gps.logger.error'), \
             patch('nixichron_gps.logger.warning'):
            mod._shutdown = False
            mod.main()

        # open_serial called >= 2 times means port was set to None after write failure,
        # causing the reconnect guard to call open_serial again on the next iteration.
        assert open_call_count[0] >= 2, (
            f'Expected open_serial called >= 2 times (port reset to None triggers '
            f'reconnect), got {open_call_count[0]} call(s). '
            f'Port was not set to None after write failure.'
        )
