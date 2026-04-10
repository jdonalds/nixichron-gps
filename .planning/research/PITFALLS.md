# Domain Pitfalls: NMEA GPS Emulator for NixiChron

**Domain:** NMEA serial time-sync emulator feeding a Nixie clock (Jeff Thomas NixiChron)
**Researched:** 2026-04-09
**Confidence:** HIGH (most pitfalls verified through official NMEA spec, pyserial docs, and community sources)

---

## Critical Pitfalls

Mistakes that cause silent failures, the clock never locks, or the entire approach needs rewriting.

---

### Pitfall 1: XOR Checksum Includes Wrong Character Range

**What goes wrong:** The checksum XOR is computed starting from (or ending at) the wrong character. The `$` and `*` delimiters must be excluded — XOR only the bytes strictly between them. A common mistake is including the `$` in the XOR (shifts all nibbles) or stopping one character too early (missing the last field character before `*`).

**Why it happens:** Off-by-one iteration in a `for` loop over the raw sentence string. For example, `sentence[1:]` correctly skips `$` but the loop must also stop before hitting `*`. Using `sentence.split('*')[0][1:]` is the safe pattern.

**Consequences:** Every sentence has a wrong checksum. A lenient parser may ignore it; a strict parser (or the NixiChron firmware) silently drops the sentence. The clock never locks and there is no error message.

**Prevention:**
- Strip from after `$` up to (not including) `*` before XOR.
- Safe Python idiom: `reduce(xor, (ord(c) for c in sentence[1:sentence.index('*')]))`
- The `--self-test` flag must validate at least 10 known sentences against expected checksums.

**Detection:** Use `--dry-run` output and cross-check against an online NMEA checksum calculator (e.g., nmeachecksum.eqth.net). Any mismatch is a bug.

**Phase:** Implementation (single-script build phase).

---

### Pitfall 2: Checksum Hex Digits Are Lowercase

**What goes wrong:** Python's `hex()` and `'%x'` format produce lowercase hex (e.g., `2a`). The NMEA 0183 standard specifies two uppercase hex digits (e.g., `2A`). Some GPS parsers accept lowercase; strict firmware may not.

**Why it happens:** Using `f'{checksum:x}'` or `hex(checksum)[2:]` without `.upper()`.

**Consequences:** NixiChron firmware may reject the sentence or interpret the checksum field as malformed. The clock either ignores sentences or flips in and out of lock intermittently.

**Prevention:** Always format as `f'{checksum:02X}'` — uppercase `X`, zero-padded to two digits.

**Detection:** Visually inspect `--dry-run` output. The checksum after `*` must always be two uppercase hex characters (A-F, not a-f).

**Phase:** Implementation.

---

### Pitfall 3: Missing or Wrong Line Terminator

**What goes wrong:** NMEA 0183 requires `\r\n` (CR+LF, `0x0D 0x0A`) as the sentence terminator. Sending only `\n` (LF) or only `\r` (CR) violates the standard. Python string literals default to `\n`.

**Why it happens:** Writing `sentence + '\n'` instead of `sentence + '\r\n'`.

**Consequences:** The NixiChron parser accumulates partial sentences across reads and never finds a complete frame. The clock may lock briefly then drop, or never lock at all.

**Prevention:** Encode each sentence as `(sentence + '\r\n').encode('ascii')` before writing to the serial port. Never use `serial.write(sentence)` on a plain string (Python 3 requires bytes).

**Detection:** Use `--dry-run` with `repr()` output to confirm `\r\n` is present. Or check the byte stream with a serial monitor.

**Phase:** Implementation.

---

### Pitfall 4: Status Field Set to 'V' (Void) Instead of 'A' (Active)

**What goes wrong:** The second field of `$GPRMC` is the data validity status. `A` = Active (valid fix). `V` = Void (no valid fix). Many emulator templates initialize this field to `V` as a safe default and then forget to set it to `A`.

**Why it happens:** Template code copied from examples that show `V` as a placeholder. Or a logic branch that incorrectly decides the data is invalid.

**Consequences:** The NixiChron firmware interprets the sentence as "no GPS lock" and refuses to set its time. The clock displays nothing or stays on its last value. This is the single most common reason a syntactically correct emulator fails to drive a GPS clock.

**Prevention:** Hard-code the status field to `A` for this emulator — it always has a "lock" because it reads NTP-synced system time. Never make this field dynamic unless detecting a genuine clock error.

**Detection:** Check field 2 in `--dry-run` output. It must be exactly `A`, not `V`, not `a`.

**Phase:** Implementation (high priority — verify in self-test).

---

### Pitfall 5: Time Is Local Time, Not UTC

**What goes wrong:** `datetime.now()` (without `timezone.utc`) returns local time. NMEA sentences always carry UTC. Sending local time disguised as UTC causes the NixiChron to display a time offset by the host's UTC offset.

**Why it happens:** Using `datetime.now()` instead of `datetime.now(timezone.utc)`. The error is silent — sentences parse correctly but the time is wrong.

**Consequences:** Clock displays the correct display format but wrong time. On a UTC-5 host the clock shows time 5 hours behind. The error is timezone-size (1–14 hours) and unlikely to be caught by format validation.

**Prevention:** Always use `datetime.now(timezone.utc)`. Pin this in code review and in the self-test (check that the emitted time matches system UTC within 1 second).

**Detection:** Compare `--dry-run` output timestamp against `date -u` in terminal. They must match within a second.

**Phase:** Implementation.

---

### Pitfall 6: Timing Drift from Naive `time.sleep(1)`

**What goes wrong:** A loop that calls `time.sleep(1)` accumulates drift because sleep duration includes loop overhead (checksum calc, string formatting, serial write latency). After one hour, the emitter may be 30–200 ms behind the wall clock second boundary.

**Why it happens:** Treating `time.sleep(1)` as a precise 1 Hz timer. It is not — it sleeps at least 1 second but is subject to scheduler jitter and loop execution time.

**Consequences:** Sentences arrive at the NixiChron mid-second rather than at the top of the second. Over hours the skew accumulates. The displayed time can lag by a visible amount. Less likely to prevent locking but causes time display to drift vs. system clock.

**Prevention:** Use deadline-based sleeping: compute the next whole-second boundary, sleep until that target.

```python
import time, math
next_tick = math.ceil(time.time())  # next whole second
while True:
    now = time.time()
    time.sleep(max(0, next_tick - now))
    send_sentence()
    next_tick += 1
```

This pattern corrects for execution time on every cycle and never accumulates drift.

**Detection:** Log `datetime.now(timezone.utc).microsecond` for each sent sentence. It should be consistently near 0 (within ~50 ms). Values drifting toward 500 ms indicate accumulated drift.

**Phase:** Implementation.

---

### Pitfall 7: Using `/dev/tty.usbserial-*` Instead of `/dev/cu.usbserial-*` on macOS

**What goes wrong:** macOS exposes two device nodes per USB-serial adapter: `tty.*` (dial-in, requires DCD assertion) and `cu.*` (calling unit, no DCD required). Opening `tty.usbserial-*` for outgoing-only serial transmission can hang on `open()` indefinitely, waiting for a carrier detect signal that will never arrive from the NixiChron.

**Why it happens:** The `tty.*` device is what appears first alphabetically, so it is often copy-pasted from documentation or tab-completed. The distinction is not obvious from the name.

**Consequences:** The script blocks forever on `serial.Serial('/dev/tty.usbserial-XXXX', 4800)` with no error or timeout. Appears as a hung process. The NixiChron receives nothing.

**Prevention:** Always use `cu.usbserial-*` (not `tty.usbserial-*`) on macOS for transmit-only serial connections. Document this explicitly in README and CLI help text. Make the default device path `/dev/cu.usbserial-XXXX` or leave it unset with a clear error if not provided.

**Detection:** Script hangs at startup with no output. Switching to the `cu.*` equivalent resolves immediately.

**Phase:** Implementation and documentation.

---

### Pitfall 8: Third-Party USB Serial Driver Not Approved on macOS (Sequoia/Sonoma/Ventura)

**What goes wrong:** CH340, CH341, Prolific PL2303, and older FTDI adapters require third-party kernel extensions or driver extensions on macOS. Since High Sierra (10.13), these must be manually approved in System Settings > Privacy & Security. The approval UI disappears 30 minutes after first connection attempt. Without approval, `ls /dev/cu.*` shows no serial device.

**Why it happens:** Plug-and-play expectation from Linux/Windows experience. macOS Sequoia (26+) has moved to Driver Extensions (dext) — some vendors have not yet shipped dext versions, leaving their adapters unsupported.

**Consequences:** No `/dev/cu.usbserial-*` device appears. Script fails with "No such file or directory". The fix requires driver installation and a reboot.

**Prevention:**
- Prefer FTDI-chipset adapters (Apple ships an FTDI dext natively for standard VID/PID, no third-party driver needed on recent macOS).
- Document driver installation steps prominently in README for CH340/Prolific adapters.
- Include a troubleshooting note: "If `/dev/cu.usbserial-*` does not appear, check Privacy & Security for a blocked driver extension."

**Detection:** `ls /dev/cu.*` returns nothing after plugging in the adapter. System Settings > Privacy & Security shows a blocked extension.

**Phase:** Documentation / setup (not a code bug, but a deployment blocker).

---

## Moderate Pitfalls

Mistakes that cause incorrect behavior but are usually debuggable.

---

### Pitfall 9: GPRMC Field Count Wrong (Missing or Extra Commas)

**What goes wrong:** The standard `$GPRMC` sentence has 12 fields in NMEA 2.3 (plus the 13th mode indicator field). Missing a field (e.g., omitting the magnetic variation direction subfield) shifts all subsequent fields. The NixiChron parser reads the date from the wrong field and may display garbage or refuse to lock.

**Why it happens:** String formatting with manual comma placement, or omitting optional fields entirely rather than leaving them empty.

**Consequences:** Date or time fields are misread. The clock may show wrong time or date, or reject the sentence entirely.

**Prevention:** Use a fixed template string with explicit empty fields for unused data:
```
$GPRMC,{time},A,0000.0000,N,00000.0000,E,0.0,0.0,{date},,,A*{checksum}\r\n
```
Empty fields (consecutive commas) are correct NMEA for absent data. Count commas: there must be exactly 11 in the body for a 12-field NMEA 2.3 sentence.

**Detection:** Count commas in `--dry-run` output. Use an NMEA validator or decoder (e.g., rl.se/gprmc) to parse the output.

**Phase:** Implementation.

---

### Pitfall 10: DTR/RTS Lines Toggling on Port Open

**What goes wrong:** When pyserial opens a serial port, it may toggle DTR and/or RTS lines to their default active state. While the NixiChron likely ignores these lines (the project uses only TX and GND), some USB-RS232 adapters generate voltage spikes on handshake lines at connect time that can confuse connected hardware.

**Why it happens:** pyserial's default behavior applies `dtr=True, rts=True` on port open. There is no connection manager that defers this.

**Consequences:** Low risk for the NixiChron (it does not use handshake lines per the wiring spec). Risk is higher if the DB9 cable is wired more fully than TX+GND.

**Prevention:** Set `dsrdtr=False, rtscts=False` explicitly in the `serial.Serial()` constructor. Set `dtr=False, rts=False` before calling `open()` if using deferred open pattern. This is defensive, not critical for this specific wiring.

**Detection:** Monitor handshake lines with a multimeter during port open if unexpected clock behavior occurs at startup.

**Phase:** Implementation (low priority but worth doing).

---

### Pitfall 11: Wrong Baud Rate (Not 4800)

**What goes wrong:** The NixiChron expects exactly 4800 baud. Sending at 9600 or any other rate produces garbage on the clock's UART receiver. The clock will not lock.

**Why it happens:** Code defaults, copy-paste from other serial projects. pyserial defaults to 9600.

**Consequences:** Clock receives corrupted data. May show flickering, random digits, or nothing.

**Prevention:** Hard-code 4800 in the `serial.Serial()` call. Do not make this a configurable parameter (it is fixed for this hardware). Add an assertion: `assert ser.baudrate == 4800`.

**Detection:** If the clock shows garbled or flickering digits but the wiring is correct, baud rate mismatch is the first thing to check.

**Phase:** Implementation.

---

### Pitfall 12: Serial Write Blocks or Raises on Disconnect

**What goes wrong:** If the USB adapter is unplugged while the script is running, `ser.write()` raises `serial.SerialException`. Without exception handling, the script dies and must be manually restarted.

**Why it happens:** No try/except around write calls. pyserial raises on OS-level write errors.

**Consequences:** The script exits. The NixiChron stops receiving sentences and may drift or revert to an internal time. Requires manual restart or a watchdog.

**Prevention:** Wrap all serial write calls in try/except for `serial.SerialException`. Implement exponential backoff reconnect (cap at 30 seconds): wait, attempt to reopen the port, resume sending.

**Detection:** Unplug the adapter during `--dry-run` equivalent, then replug and verify reconnect.

**Phase:** Implementation (resilience / error handling).

---

### Pitfall 13: SIGINT/SIGTERM Does Not Close the Serial Port

**What goes wrong:** If the script is killed with Ctrl-C or `systemctl stop`, the serial port file descriptor may not be closed cleanly. On Linux the port is released by the OS; on macOS the `cu.*` device can remain in a locked state for several seconds, causing the next invocation to fail with "Resource busy."

**Why it happens:** No signal handler; the default SIGINT raises `KeyboardInterrupt` which may skip `finally` blocks if the exception is not caught.

**Consequences:** Restarting the script fails until the OS releases the device. Systemd unit restarts loop and never succeeds.

**Prevention:** Install explicit signal handlers for SIGTERM and SIGINT. Call `ser.close()` in a `finally` block and in the signal handler before `sys.exit(0)`.

**Detection:** Start script, Ctrl-C, immediately restart — if it fails with "Resource busy" the port was not released.

**Phase:** Implementation.

---

## Minor Pitfalls

Small mistakes that are easy to fix but annoying to diagnose.

---

### Pitfall 14: Date Format Is ddmmyy, Not yymmdd

**What goes wrong:** The GPRMC date field is `ddmmyy` (day first, then month, then two-digit year). Python's `strftime('%y%m%d')` produces `yymmdd`. Using the wrong format code produces a valid-looking but wrong date.

**Why it happens:** Confusing ISO date format with NMEA date format.

**Prevention:** Use `strftime('%d%m%y')` — day first. Add a comment in code: `# NMEA date is ddmmyy, NOT yymmdd`.

**Detection:** Inspect `--dry-run` output. In April 2026, field 9 must be `090426` (09=day, 04=month, 26=year).

**Phase:** Implementation.

---

### Pitfall 15: Time Format Omits or Truncates Subseconds

**What goes wrong:** The GPRMC time field format is `hhmmss.ss`. Some implementations omit the `.ss` fractional part (`hhmmss`) or include full microseconds. Either may confuse strict parsers.

**Why it happens:** Using `strftime('%H%M%S')` without the fractional part, or formatting microseconds directly.

**Prevention:** Always include `.00` if not using fractional seconds: `strftime('%H%M%S') + '.00'`. This matches common GPS receiver output.

**Detection:** Check field 1 of `--dry-run` output for `.` decimal and exactly two decimal places.

**Phase:** Implementation.

---

### Pitfall 16: Emitter Sends Sentences After the Second Boundary Rather Than At It

**What goes wrong:** The sentence is built after the top-of-second sleep wakeup, which takes a small but nonzero amount of time. If the script wakes up at exactly T=1.000 but then calls `datetime.now(timezone.utc)` after 2ms of overhead, the time field in the sentence correctly reflects T+2ms — which is still the correct second. However, if the overhead slips past 999ms (unlikely but possible on a loaded system), the sentence carries the wrong second.

**Why it happens:** No guarantee on scheduler wakeup latency.

**Consequences:** Extremely rare one-second error in displayed time on a heavily loaded machine. Not a correctness bug under normal conditions.

**Prevention:** Read the clock immediately after waking — the first line after the sleep should be the `datetime.now(timezone.utc)` call. Minimize any computation before the clock read.

**Phase:** Implementation (low priority).

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Checksum implementation | Wrong XOR range, lowercase hex | Self-test with known sentences |
| GPRMC field formatting | Status='V', wrong date format, missing CRLF | Dry-run + NMEA validator |
| Serial port setup | tty.* vs cu.* on macOS, wrong baud, DTR toggle | Use cu.*, hard-code 4800 |
| Timing loop | Naive sleep(1) drift | Deadline-based sleep |
| Driver installation | Unsigned kext blocked on macOS Sequoia/Sonoma | FTDI adapter preferred; README driver steps |
| Signal / cleanup | Port stays locked on SIGINT | finally block + signal handler |
| Reconnect logic | Script dies on unplug | SerialException catch + backoff |

---

## Sources

- NMEA 0183 Sentence Specification (gpsd project): https://gpsd.gitlab.io/gpsd/NMEA.html
- NMEA checksum XOR range explanation: https://rietman.wordpress.com/2008/09/25/how-to-calculate-the-nmea-checksum/
- NMEA checksum case: https://docs.inertialsense.com/user-manual/com-protocol/nmea/
- pyserial DTR/RTS on open (GitHub issue #124): https://github.com/pyserial/pyserial/issues/124
- pyserial reconnect (GitHub issue #558): https://github.com/pyserial/pyserial/issues/558
- macOS tty.* vs cu.* for outgoing serial: https://copyprogramming.com/howto/choosing-between-dev-tty-usbserial-vs-dev-cu-usbserial
- macOS USB serial driver approval (Ventura/Sonoma/Sequoia): https://www.mac-usb-serial.com/docs/support/troubleshooting.html
- NixiChron GPS input ($GPRMC, 4800 baud, status=A): https://groups.google.com/g/neonixie-l/c/uxxNlaHVkC8/m/WSEAKJfPsYUJ
- Accurate 1-second Python interval (deadline sleep pattern): https://forums.raspberrypi.com/viewtopic.php?t=296615
- GPRMC field breakdown reference: https://gist.github.com/tomfanning/60f94e547c979907e32030c9df7f1272
