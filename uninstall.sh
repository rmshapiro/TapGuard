#!/usr/bin/env bash
set -euo pipefail
# Disable future starts before trying recovery; preserve settings and backups.
rm -f "$HOME/.config/autostart/tapguard-v3.desktop"
if [[ -f "$HOME/bin/tapguard.py" ]]; then
  python3 "$HOME/bin/tapguard.py" --ctl stop >/dev/null 2>&1 || true
fi
# Wait for the supervisor's recovery and lock release before issuing recovery.
if ! python3 - <<'PYWAIT'
import fcntl, time
from pathlib import Path
path = Path.home() / '.cache/tapguard/daemon.lock'
if path.exists():
    with path.open('a+') as lock:
        deadline = time.monotonic() + 15
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise SystemExit(1)
                time.sleep(0.1)
PYWAIT
then
  echo 'Autostart disabled, but controller is still running. Stop its terminal or log out before recovery.' >&2
  exit 1
fi
failed=0
xinput enable 'Apple SPI Touchpad' || failed=1
xinput set-prop 'Apple SPI Touchpad' 'libinput Tapping Enabled' 1 || failed=1
if [[ "$failed" -ne 0 ]]; then
  echo 'Autostart disabled, but touchpad recovery could not be confirmed. See README recovery instructions.' >&2
  exit 1
fi
echo 'Autostart disabled; recovery commands succeeded. Confirm pointer and tapping work.'
echo 'Remove TapGuard from the Cinnamon panel. Installed files, settings and backups remain.'
