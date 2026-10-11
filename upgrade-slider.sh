#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET="$HOME/bin/tapguard.py"
if [[ ! -f "$TARGET" ]]; then
  echo "TapGuard v3 isn't installed at $TARGET. Run ./install.sh instead."
  exit 1
fi
if ! grep -q 'TapGuard v3:' "$TARGET" && ! grep -q 'TapGuard v3.1:' "$TARGET"; then
  echo "Unexpected TapGuard version at $TARGET. No changes made."
  exit 1
fi
python3 -m py_compile "$HERE/tapguard.py"
BACKUP="$HOME/bin/tapguard-before-v3.1-$(date +%Y%m%d-%H%M%S).py"
cp -p "$TARGET" "$BACKUP"
install -m 755 "$HERE/tapguard.py" "$TARGET"
echo "Updated the Tk slider in $TARGET"
echo "Backup: $BACKUP"
echo 'Close any open TapGuard Settings window, then open Settings from the panel again.'
echo 'The controller and panel applet can remain running; saved settings are unchanged.'
