#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ "$EUID" -ne 0 ]] || { echo 'Run without sudo.'; exit 1; }
TARGET="$HOME/.local/share/cinnamon/applets/tapguard@local"
[[ -f "$TARGET/applet.js" && -f "$HOME/bin/tapguard.py" ]] || { echo 'Existing TapGuard installation not found. Use install.sh for a new installation.'; exit 1; }
BACKUP="${TARGET}-before-3.1.1-$(date +%Y%m%d-%H%M%S)"
cp -a "$TARGET" "$BACKUP"
install -m 644 "$HERE/cinnamon/tapguard@local/applet.js" "$HERE/cinnamon/tapguard@local/metadata.json" "$TARGET/"
printf '%s\n' "Applet updated. Backup: $BACKUP" 'Log out and back in to reload the applet. Controller and settings were not changed.'
