# TapGuard v3.1

Trackpad protection while typing, with a Cinnamon panel countdown and a small settings window.

TapGuard targets **Linux Mint Cinnamon on X11 with an Apple SPI Touchpad**. It watches keyboard press activity, temporarily blocks the trackpad (or just tap-to-click), and restores it after a configurable idle delay of 0.5–5 seconds. The initial default is full trackpad lockout with a 1.5-second delay; existing settings take precedence.

## Platform and verification

The original v3.1 package describes a 2016 MacBook Pro without Touch Bar running Linux Mint 22.3 Cinnamon/X11. The packaging environment was directly verified as Mint 22.3, Cinnamon 6.6.9, X11. That environment check is **not a fresh hardware acceptance test**.

Automated checks cover controller logic with mocked XInput calls. Real trackpad behavior, crash recovery, Cinnamon applet behavior, Tk slider interaction and login autostart still require on-device acceptance testing for this repackaged release. No cross-distro, other desktop, other touchpad, or Wayland support is claimed. The device name is currently fixed to `Apple SPI Touchpad`; this is not a generic touchpad utility.

## Features

- Full lockout: blocks pointer motion, scrolling and clicks while typing.
- Tap-only: blocks tap-to-click while preserving pointer motion and physical clicks.
- Panel countdown, pause/resume, mode controls and settings launcher.
- Tk settings window; closing it leaves the controller running.
- A separate supervisor attempts recovery if its worker exits.
- Per-user installation and Cinnamon login autostart, without root access.

## Install

Download `TapGuard-v3.1.zip` from the v3.1 release, extract it, and open a terminal in the extracted `TapGuard` folder. Install prerequisites on the target Mint system:

```bash
sudo apt install python3 python3-tk xinput coreutils
```

Close older TapGuard versions and remove their Startup Applications entries before installing. Run the following **without sudo** from your Cinnamon/X11 session:

```bash
bash install.sh
python3 ~/bin/tapguard.py --daemon
```

The installer enables autostart for subsequent Cinnamon logins. It installs the controller at `~/bin/tapguard.py`, the applet at `~/.local/share/cinnamon/applets/tapguard@local/`, and the startup entry at `~/.config/autostart/tapguard-v3.desktop`. Existing controller files are backed up and settings are preserved.

Keep the first controller terminal open. In a second terminal:

```bash
python3 ~/bin/tapguard.py --gui
```

Start with tap-only mode and keep an external mouse available during testing. Verify typing, idle restoration, pause/resume and Ctrl+C recovery before relying on full lockout. Add **TapGuard** through Cinnamon panel → Applets → Manage. Log out and back in if Cinnamon does not discover the applet.

## Controls

```bash
python3 ~/bin/tapguard.py --ctl status
python3 ~/bin/tapguard.py --ctl mode tap
python3 ~/bin/tapguard.py --ctl mode full
python3 ~/bin/tapguard.py --ctl delay 2.0
python3 ~/bin/tapguard.py --ctl pause
python3 ~/bin/tapguard.py --ctl resume
python3 ~/bin/tapguard.py --ctl stop
```

Settings live in `~/.config/tapguard.json`. The local socket, status file, lock and diagnostic log live in `~/.cache/tapguard/`.

## Recovery and limitations

Recovery is best effort, not guaranteed. The supervisor cannot recover a hung worker that never exits, termination of both processes, or loss of the X11 session. XInput commands can also fail. Restoration explicitly enables both the device and tap-to-click, even if your normal tapping preference was off.

If the trackpad remains blocked, use an external mouse or keyboard to open a terminal. Stop the controller, then restore the device:

```bash
python3 ~/bin/tapguard.py --ctl stop
xinput enable 'Apple SPI Touchpad'
xinput set-prop 'Apple SPI Touchpad' 'libinput Tapping Enabled' 1
```

If it locks again, the controller may still be running: stop its foreground terminal with Ctrl+C, disable the startup entry as shown below, and log out or reboot. Login resets session-scoped XInput state; disabling autostart prevents immediate recurrence. Recovery commands need the affected desktop's X11 session and are not expected to work from an unrelated text console.

## Uninstall / disable

From the extracted folder:

```bash
bash uninstall.sh
```

This disables autostart, requests controller shutdown, and attempts trackpad recovery. It reports recovery errors rather than claiming success. Remove TapGuard from the Cinnamon panel. Installed files, backups and settings remain for rollback. After confirming the controller has stopped and removing the applet, you may delete `~/bin/tapguard.py`, `~/.local/share/cinnamon/applets/tapguard@local/`, `~/.config/tapguard.json` and `~/.cache/tapguard/` if no longer wanted.

To disable future starts manually:

```bash
rm -f ~/.config/autostart/tapguard-v3.desktop
```

To roll back, stop TapGuard and restore your timestamped `~/bin/tapguard-before-v3.1-*.py` backup. Restore an older startup entry only if you deliberately want that older version to start.

## Privacy and security

The Python source does not save or transmit typed characters and contains no network client. It reads the system-wide X11 event stream and uses only `RawKeyPress` activity; X11 event monitoring is inherently sensitive, so review the source before running it. It does not require root or alter kernel modules or Kinto configuration.

XInput is invoked with argument lists rather than shell interpolation. The control socket is local and mode 0600; controller-created files use a restrictive umask. Commands are limited to the documented controls. Processes already running as your desktop user remain within the same trust boundary. Logs contain operational errors, not a keyboard event transcript.

## Development checks

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile tapguard.py
bash -n install.sh uninstall.sh upgrade-slider.sh
```

See [CHANGELOG.md](CHANGELOG.md) and [RELEASE-NOTES.md](RELEASE-NOTES.md). The original `upgrade-slider.sh` is retained for historical GUI-only upgrades; use the full installer to obtain the release's controller and installer changes.

## License

MIT; see [LICENSE](LICENSE). The source archive contained no pre-existing license or third-party attribution notices. This repository applies the owner's requested MIT license to the supplied project; installed system dependencies retain their own licenses.
