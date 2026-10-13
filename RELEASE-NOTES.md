# TapGuard v3.2 — Palm lockout

Adds a persistent Palm mode based on the owner-verified prototype: any size-classified palm blocks the entire touchpad until that contact lifts. Keyboard activity causes no delay in this mode. Existing typing modes are retained.

Includes Cinnamon/Settings controls, saved selection, stale-sensor fail-open behavior, reconnection attempts, event-drop resynchronization and restoration of libinput's original typing-protection setting. Palm mode needs one-time, touchpad-only uaccess setup; no root process runs during normal operation.

Existing users: run `bash upgrade-palm.sh` without sudo. It requests sudo for device access, backs up the old installation, preserves startup preferences and activates/saves Palm mode. Log out/in to refresh the panel. See README.md for new installation, recovery, limitations and rollback.

The owner verified the persistent installation after logout/login on October 13, 2026: full palm lockout, immediate release, no errant cursor movement, accurate panel status and login startup. All 22 automated tests pass, along with Python/JavaScript/shell syntax and udev rule checks. Reconnect, suspend and screen-reader behavior have not been independently verified.
