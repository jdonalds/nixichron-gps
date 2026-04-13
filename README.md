# NixiChron GPS Emulator

A Python daemon that feeds a Jeff Thomas NixiChron Nixie tube clock with accurate UTC time over RS-232 — no real GPS module required. It reads the host's NTP-synced system clock and formats it as standard NMEA $GPRMC sentences at 1 Hz.

## Requirements

- Python 3.9+
- USB-to-RS232 adapter (DB9 female connector, RS-232 voltage levels — not TTL)
- FTDI-chipset adapter recommended (see Troubleshooting for macOS driver notes)
- Jeff Thomas NixiChron clock with 6-pin mini-DIN GPS input

## Hardware Wiring

Connect the DB9 female connector on your USB adapter to the 6-pin mini-DIN GPS port on the NixiChron clock.

```
  DB9 Female (USB adapter)              6-Pin Mini-DIN (NixiChron GPS port)
  +---------------------------+          +----------------------------------+
  | Pin 3  TX (transmit data) |--------->| Pin 5  RX (clock receive)        |
  | Pin 5  GND (ground)       |--------->| Pin 1  GND (ground)              |
  |                           |          | Pin 2  DO NOT CONNECT (+5V rail) |
  |                           |          | Pin 4  Leave floating            |
  +---------------------------+          +----------------------------------+
```

| DB9 Pin | Signal | Mini-DIN Pin | Action              |
|---------|--------|--------------|---------------------|
| 3       | TX     | 5            | Connect             |
| 5       | GND    | 1            | Connect             |
| —       | —      | 2            | **DO NOT CONNECT**  |
| —       | —      | 4            | Leave floating      |

**WARNING: Mini-DIN pin 2 carries the clock's +5V power rail. Connecting it to the DB9 adapter will damage hardware.**

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/nixichron-gps-emulator.git
cd nixichron-gps-emulator
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your user to the dialout group (Linux only)

Serial ports on Linux are owned by the `dialout` group. Without membership, the script will fail with `Permission denied`.

```bash
sudo usermod -aG dialout $USER
```

**Log out and back in** for the group change to take effect. Verify with `groups` — you should see `dialout` in the output.

### 4. Find your serial device

**Linux:**
```bash
ls /dev/ttyUSB*
# Typical output: /dev/ttyUSB0
```

**macOS — always use cu.* not tty.*:**
```bash
ls /dev/cu.*
# Typical output: /dev/cu.usbserial-XXXX
```

See Troubleshooting if no device appears.

## Running

### Dry run (no serial port required)

Verify the script produces correctly-formatted sentences before connecting hardware:

```bash
python3 src/nixichron_gps.py --dry-run
```

Each line should begin with `$GPRMC`, contain a timestamp matching `date -u`, and end with a two-hex-digit checksum.

### Self-test

Verify all five generated sentences have correct checksums:

```bash
python3 src/nixichron_gps.py --self-test
```

All lines should end with `PASS`. Exit code 0 on success.

### Live mode

```bash
# Linux
python3 src/nixichron_gps.py --port /dev/ttyUSB0

# macOS
python3 src/nixichron_gps.py --port /dev/cu.usbserial-0001
```

The port can also be set via environment variable:

```bash
GPS_PORT=/dev/cu.usbserial-0001 python3 src/nixichron_gps.py
```

Add `--verbose` or `-v` to see each sentence logged at DEBUG level.

Stop with Ctrl-C (SIGINT) or `kill <pid>` (SIGTERM). The serial port is always closed cleanly on shutdown.

## Systemd Service (Linux)

Install the daemon as a systemd service so it starts automatically on boot.

### 1. Edit the unit file

Open `nixichron-gps.service` and replace the two placeholder values:

```ini
User=YOUR_USERNAME          # replace with your Linux username (e.g. User=alice)
ExecStart=/usr/bin/python3 /path/to/src/nixichron_gps.py
#                          ^ replace with the absolute path to the script
#                            Run: realpath src/nixichron_gps.py
```

Find the values you need:

```bash
whoami                         # your username
which python3                  # path to Python (use this in ExecStart)
realpath src/nixichron_gps.py  # absolute path to the script
```

### 2. Install and enable

```bash
sudo cp nixichron-gps.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nixichron-gps
```

### 3. Check status

```bash
sudo systemctl status nixichron-gps
journalctl -u nixichron-gps -f
```

### Using GPS_PORT environment variable

Alternatively, keep `ExecStart` generic and set the port via environment:

```ini
[Service]
Environment=GPS_PORT=/dev/ttyUSB0
ExecStart=/usr/bin/python3 /path/to/src/nixichron_gps.py
```

## Troubleshooting

### Clock not locking (display unchanged after 10+ seconds)

1. **Check wiring.** Confirm DB9 pin 3 goes to mini-DIN pin 5 and DB9 pin 5 goes to mini-DIN pin 1. Use a multimeter in continuity mode to verify.

2. **Check the device exists.**
   - Linux: `ls /dev/ttyUSB0`
   - macOS: `ls /dev/cu.*`
   
   If nothing appears, the adapter is not recognized — check driver installation (see macOS section below).

3. **Check permissions (Linux).**
   ```bash
   ls -la /dev/ttyUSB0
   ```
   If you see `crw-rw---- 1 root dialout`, your user is not in the `dialout` group. Run `sudo usermod -aG dialout $USER`, log out and back in.

4. **Verify TX output with a loopback test.** Connect DB9 pin 3 to DB9 pin 2 on the adapter (TX to RX loopback). Then in one terminal:
   ```bash
   python3 src/nixichron_gps.py --dry-run --port /dev/ttyUSB0
   ```
   In a second terminal:
   ```bash
   cat /dev/ttyUSB0      # Linux
   cat /dev/cu.usbserial-XXXX  # macOS
   ```
   NMEA sentences should appear in the second terminal. If they do not, the adapter is not transmitting.

### Clock counting from 00:00 (not using system time)

The clock received sentences but is not accepting the time. Two possible causes:

1. **Status field is not A.** Run `python3 src/nixichron_gps.py --dry-run | head -3`. Field 2 (zero-indexed) in each sentence must be `A`:
   ```
   $GPRMC,123456.00,A,0000.0000,...
                    ^-- must be A, not V
   ```

2. **Time is not UTC.** Compare the timestamp in `--dry-run` output to `date -u`. They must match within 1 second. If they differ by whole hours, the host system clock is set to local time instead of UTC — fix the host clock timezone.

### Script hangs at startup with no output or error — macOS only

You are using a `tty.*` device. On macOS, `tty.*` devices are dial-in and block `open()` until DCD is asserted. The NixiChron never asserts DCD, so the open call never returns.

**Always use `cu.*` on macOS:**
```bash
# Wrong — will hang:
python3 src/nixichron_gps.py --port /dev/tty.usbserial-XXXX

# Correct:
python3 src/nixichron_gps.py --port /dev/cu.usbserial-XXXX
```

List available devices: `ls /dev/cu.*`

### No /dev/cu.* device appears after plugging in adapter — macOS only

Your adapter requires a third-party kernel extension that macOS has blocked.

1. Open **System Settings > Privacy & Security** and scroll to the bottom. Look for a blocked system extension from your adapter's manufacturer and click **Allow**. Restart your Mac.

2. If no blocked extension appears, your adapter's chipset (commonly CH340 or Prolific) may not have a driver compatible with your macOS version.

**Recommendation:** Use an FTDI-chipset USB-serial adapter. macOS includes native FTDI driver support (no third-party install needed). Look for adapters labeled "FTDI FT232" chipset.
