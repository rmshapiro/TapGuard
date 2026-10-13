#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$EUID" -ne 0 ]] || { echo 'Run without sudo; access setup requests sudo separately.'; exit 1; }
[[ -f "$HOME/bin/tapguard.py" ]] || { echo 'Install TapGuard with install.sh first.'; exit 1; }
# Obtain and verify touchpad access before touching the working installation.
bash "$HERE/enable-palm-access.sh"
python3 -m py_compile "$HERE/tapguard.py" "$HERE/palm.py"
BACKUP="$HOME/.local/share/tapguard/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP"
cp -p "$HOME/bin/tapguard.py" "$BACKUP/tapguard.py"
[[ ! -f "$HOME/bin/palm.py" ]] || cp -p "$HOME/bin/palm.py" "$BACKUP/palm.py"
[[ ! -f "$HOME/.config/tapguard.json" ]] || cp -p "$HOME/.config/tapguard.json" "$BACKUP/tapguard.json"
[[ ! -d "$HOME/.local/share/cinnamon/applets/tapguard@local" ]] || cp -a "$HOME/.local/share/cinnamon/applets/tapguard@local" "$BACKUP/applet"
STARTUP="$HOME/.config/autostart/tapguard-v3.desktop"
[[ ! -f "$STARTUP" ]] || cp -p "$STARTUP" "$BACKUP/autostart.desktop"
python3 "$HOME/bin/tapguard.py" --ctl stop || true
# Wait until the existing supervisor has released its lock.
python3 - <<'PY'
import fcntl,time
from pathlib import Path
p=Path.home()/'.cache/tapguard/daemon.lock';p.parent.mkdir(parents=True,exist_ok=True)
with p.open('a+') as f:
    for _ in range(100):
        try:
            fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
            break
        except BlockingIOError: time.sleep(.1)
    else: raise SystemExit('Old controller still running. Stop it before upgrading.')
PY
bash "$HERE/install.sh"
# Preserve the exact previous startup preference.
if [[ -f "$BACKUP/autostart.desktop" ]]; then
  cp -p "$BACKUP/autostart.desktop" "$STARTUP"
else
  rm -f "$STARTUP"
fi
nohup /usr/bin/python3 "$HOME/bin/tapguard.py" --daemon >> "$HOME/.cache/tapguard/upgrade.log" 2>&1 </dev/null &
python3 - <<'PY'
import json,subprocess,time
from pathlib import Path
script=str(Path.home()/'bin/tapguard.py')
for _ in range(100):
    try:
        p=subprocess.run(['/usr/bin/python3',script,'--ctl','mode','palm'],capture_output=True,text=True,timeout=3)
        s=json.loads(p.stdout)
        if s.get('ok'):
            print('Palm lockout enabled and saved. No typing cooldown.')
            break
    except (ValueError,subprocess.SubprocessError): pass
    time.sleep(.1)
else: raise SystemExit('Palm reader did not become ready. Existing mode retained; inspect ~/.cache/tapguard/tapguard.log.')
PY
printf '%s\n' "Backup: $BACKUP" 'Controller is running in palm mode now. Log out/in to refresh the panel menu.'
