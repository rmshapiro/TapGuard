#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$EUID" -ne 0 ]] || { echo 'Run as your desktop user, without sudo.'; exit 1; }
[[ "${XDG_SESSION_TYPE:-}" == x11 && -n "${DISPLAY:-}" ]] || { echo 'Requires a Cinnamon/X11 desktop session. Wayland is unsupported.'; exit 1; }
case "${XDG_CURRENT_DESKTOP:-}" in
  *Cinnamon*|*cinnamon*) ;;
  *) echo 'This package targets Cinnamon only.'; exit 1 ;;
esac
for prog in xinput python3 stdbuf; do
  command -v "$prog" >/dev/null || { echo "Missing dependency: $prog"; exit 1; }
done
python3 -c 'import tkinter' || { echo 'Missing Tk: sudo apt install python3-tk'; exit 1; }
xinput list-props 'Apple SPI Touchpad' >/dev/null || { echo 'Apple SPI Touchpad not found. No files installed.'; exit 1; }
if [[ -f "$HOME/bin/tapguard.py" ]] && python3 "$HOME/bin/tapguard.py" --ctl status >/dev/null 2>&1; then
  echo 'Stop the existing controller before upgrading: python3 ~/bin/tapguard.py --ctl stop'
  exit 1
fi
mkdir -p "$HOME/bin" "$HOME/.config/autostart" "$HOME/.local/share/cinnamon/applets/tapguard@local"
if [[ -f "$HOME/bin/tapguard.py" ]]; then
  cp -p "$HOME/bin/tapguard.py" "$HOME/bin/tapguard-before-v3.2-$(date +%Y%m%d-%H%M%S).py"
fi
install -m 755 "$HERE/tapguard.py" "$HOME/bin/tapguard.py"
install -m 644 "$HERE/palm.py" "$HOME/bin/palm.py"
install -m 644 "$HERE/cinnamon/tapguard@local/metadata.json" "$HERE/cinnamon/tapguard@local/applet.js" "$HOME/.local/share/cinnamon/applets/tapguard@local/"
python3 - <<'PY'
from pathlib import Path
# Desktop Entry Exec quoting, including its separate string escape layer.
script = str(Path.home() / 'bin' / 'tapguard.py')
for char in ('\\', '"', '`', '$'):
    script = script.replace(char, '\\' + char)
script = script.replace('\\', '\\\\').replace('%', '%%')
entry = '[Desktop Entry]\nType=Application\nName=TapGuard v3.2\nComment=Trackpad protection while typing\nExec=/usr/bin/python3 "' + script + '" --daemon\nTerminal=false\nX-GNOME-Autostart-enabled=true\nOnlyShowIn=X-Cinnamon;\n'
path = Path.home() / '.config/autostart/tapguard-v3.desktop'
path.write_text(entry)
path.chmod(0o644)
PY
printf '%s\n' 'Installed TapGuard v3.2; autostart is enabled for future Cinnamon logins.' \
 'Close all old TapGuard processes before starting this version.' \
 'Test now: python3 ~/bin/tapguard.py --daemon (Ctrl+C to stop)' \
 'Settings: python3 ~/bin/tapguard.py --gui' \
 'Add TapGuard via Cinnamon panel > Applets.'
