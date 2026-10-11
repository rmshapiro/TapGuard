# TapGuard v3.1

Typing protection for Linux Mint Cinnamon/X11 with the Apple SPI Touchpad. Includes the v3.1 live delay slider fix, Cinnamon applet, controller supervisor, per-user installer and uninstall/disable helper.

This release is based on the original downloaded `tapguard-v3.1.zip`, with documented publication fixes for recovery cleanup, local control handling, installer checks and desktop entry quoting. It is not byte-identical to the original archive.

Target environment: Linux Mint 22.3, Cinnamon 6.6.9, X11; original package identifies a 2016 MacBook Pro without Touch Bar. No other distributions, desktops, devices or Wayland are claimed supported.

Automated controller tests and syntax checks pass. Physical trackpad recovery, GUI, applet and login acceptance testing has not been repeated for this repackaged build. Keep an external mouse available during initial full-lockout testing. Read the README recovery instructions before enabling protection.

Download `TapGuard-v3.1.zip`, extract it, then run `bash install.sh` without sudo. MIT licensed.
