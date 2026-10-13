# TapGuard v3.2 — Palm lockout

Palm down: block the entire Apple SPI Touchpad, including other fingers, movement, scrolling, taps and physical clicks. Palm lifted: restore input without a typing cooldown. Existing typing-based full and tap-only modes remain available.

Targets Linux Mint Cinnamon/X11 and Apple SPI Touchpad. Uses the contact-size threshold of 1600 successfully tested by the owner on October 13, 2026. A contact remains classified as palm until it lifts. This is not a generic touchpad or Wayland utility.

## Upgrade an existing installation

Extract TapGuard-v3.2.zip and open a terminal in the TapGuard folder. Run as your desktop user, without sudo:

```bash
bash upgrade-palm.sh
```

The access setup prompts for sudo once. It installs `/etc/udev/rules.d/70-tapguard-palm.rules`, granting the active desktop user access to only the named Apple SPI Touchpad event device. It does not add you to the input group or grant keyboard access. Other programs running as that user may also access this touchpad; the standard uaccess ACL grants read/write access, although TapGuard only reads events.

The upgrade verifies access before stopping the old controller. It backs up the controller, applet, config and startup entry under `~/.local/share/tapguard/backups/`, installs both controller modules and the applet, preserves the previous autostart entry or its absence, starts the controller and selects/saves Palm mode. Your previous delay remains saved for typing modes. Log out/in to reload Cinnamon's menu. Palm mode is active immediately after the upgrade command succeeds.

## New installation

Install prerequisites:

```bash
sudo apt install python3 python3-tk python3-evdev xinput coreutils
bash enable-palm-access.sh
bash install.sh
python3 ~/bin/tapguard.py --daemon
```

Keep that terminal open. In another terminal, after the reader has started:

```bash
python3 ~/bin/tapguard.py --ctl mode palm
```

The full installer enables Cinnamon login autostart. Add TapGuard via panel → Applets. Initial mode remains full typing lockout until Palm mode is selected; existing saved settings take precedence.

## Controls

Panel and Settings offer Palm lockout, typing full lockout and typing tap-only. Palm mode disables the typing-delay slider and displays Palm/Ready rather than a countdown. Pause restores input and the original libinput typing-protection setting. Resume returns to the selected mode. Selecting another mode restores the original libinput typing setting; Palm mode turns it off only while protection is enabled and the sensor is ready.

```bash
python3 ~/bin/tapguard.py --gui
python3 ~/bin/tapguard.py --ctl status
python3 ~/bin/tapguard.py --ctl mode palm
python3 ~/bin/tapguard.py --ctl mode full
python3 ~/bin/tapguard.py --ctl mode tap
python3 ~/bin/tapguard.py --ctl pause
python3 ~/bin/tapguard.py --ctl resume
python3 ~/bin/tapguard.py --ctl stop
```

Settings: `~/.config/tapguard.json`. Status/socket/log/recovery data: `~/.cache/tapguard/`. The socket is local and 0600. No typed characters or touch coordinates are logged or transmitted. Typing fallback uses X11 key activity; the separate palm reader opens input devices only to identify the named touchpad and reads only that device's events.

## Recovery and limitations

Missing, stale or disconnected palm input restores normal trackpad operation; the reader retries access and reconnection. The panel reports Sensor offline rather than silently switching to typing lockout. Kernel event drops trigger a fresh slot snapshot; pause/stop/shutdown restore input, and the supervisor attempts recovery if the worker exits. A small recovery file preserves the original libinput typing setting through a worker crash.

Recovery is best effort if X11/xinput fails or both processes are killed. Initial contact can leak briefly before the separate XInput disable operation. This is a userspace gate, not an atomic driver filter. Re-enabling X input may require lifting and replacing an already-down finger. Threshold tuning, suspend/resume, screen-reader behavior and broader hardware acceptance need on-device verification. Normal paused behavior may include the original libinput typing timeout.

If input stays blocked, use your keyboard or external mouse to stop the controller and restore input:

```bash
python3 ~/bin/tapguard.py --ctl stop
xinput enable 'Apple SPI Touchpad'
xinput set-prop 'Apple SPI Touchpad' 'libinput Tapping Enabled' 1
xinput set-prop 'Apple SPI Touchpad' 'libinput Disable While Typing Enabled' 1
```

The final value 1 matches this owner's original typing-protection setting; use your previous value if different. Disable the startup entry and log out/in if recovery does not hold. Avoid running the temporary palm test alongside the permanent controller.

## Rollback / uninstall

Run `bash uninstall.sh` to stop protection and disable autostart. It leaves files/settings for rollback. To roll back, stop the controller, restore `tapguard.py`, the applet folder, `tapguard.json` and the autostart entry from the printed backup directory, then log out/in. Older v3.1 controllers ignore `palm` mode, so restore the saved config as well. The extra `~/bin/palm.py` can remain unused.

To remove the new access rule after stopping Palm mode:

```bash
sudo rm /etc/udev/rules.d/70-tapguard-palm.rules
sudo udevadm control --reload-rules
```

Log out/in (or reboot) to refresh device ACLs. The user is not added to any group and no root daemon or passwordless sudo rule is installed.

## Development checks

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile tapguard.py palm.py
node --check cinnamon/tapguard@local/applet.js
node tests/test_applet.js
bash -n install.sh uninstall.sh upgrade-palm.sh enable-palm-access.sh
udevadm verify 70-tapguard-palm.rules
```

The owner confirmed the temporary prototype's palm-plus-thumb suppression and immediate unlock. The persistent v3.2 integration requires a fresh on-device check after installation. Automated checks use mocked input commands; they do not establish hardware or login acceptance.

MIT licensed; see LICENSE. System dependencies retain their own licenses.
