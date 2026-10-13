#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" -ne 0 ]] || { echo 'Run as your desktop user, without sudo.'; exit 1; }
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python3 -c 'import evdev' || { echo 'Install dependency first: sudo apt install python3-evdev'; exit 1; }
NODE="$(xinput list-props 'Apple SPI Touchpad' | sed -n 's/.*Device Node.*"\([^"]*\)".*/\1/p')"
[[ "$NODE" =~ ^/dev/input/event[0-9]+$ ]] || { echo 'Apple touchpad device not found.'; exit 1; }
# uaccess is scoped to this named event device and the active local seat user.
# The rule runs before 73-seat-late.rules applies the ACL.
sudo install -m 644 "$HERE/70-tapguard-palm.rules" /etc/udev/rules.d/70-tapguard-palm.rules
sudo udevadm control --reload-rules
sudo udevadm trigger --action=change --subsystem-match=input --sysname-match="${NODE##*/}"
sudo udevadm settle
python3 - "$NODE" <<'PY'
import sys
from evdev import InputDevice
x = InputDevice(sys.argv[1])
try:
    if x.name != 'Apple SPI Touchpad': raise SystemExit('Unexpected input device')
    print('Touchpad access verified. Keyboard access was not granted.')
finally:
    x.close()
PY
