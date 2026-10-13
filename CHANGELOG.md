# v3.2.0

- Add saved Palm lockout mode: whole trackpad blocked while any palm contact remains; no typing delay.
- Keep typing modes and delay setting; add matching panel and Tk controls.
- Add raw multitouch slot tracking, stale-reader fail-open recovery, reconnect and event-drop resynchronization.
- Restore original libinput typing-protection setting on pause/mode exit/shutdown.
- Add touchpad-only uaccess setup and full upgrade with backup and preserved autostart preference.
- Persistent mode, login startup and panel status verified by owner on October 13, 2026.

# v3.1.1

- Show confirmed Cinnamon menu mode with native radio selection, actionable labels and accessible checked state.
- Add applet-only upgrade with backup; controller and settings unchanged.

# Changelog

## v3.1

- Original v3.1: live Tk delay label and stable slider position while dragging.
- Publication preparation: explicit X11 startup checks, restrictive controller file permissions, bounded control request queue and JSON object validation.
- Force a recovery attempt during worker cleanup and continue cleanup after recovery errors.
- Installer: Cinnamon/X11 and dependency checks, quoted desktop entry paths, v3.1 labels and applet version.
- Uninstaller: disable autostart first and report failed recovery commands.
- Add MIT license, platform limitations, recovery instructions and release documentation.
