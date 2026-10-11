# TapGuard v3.1.1 — Cinnamon mode selection fix

Based on the published TapGuard v3.1 source. The controller and existing installation scripts are unchanged.

The selected protection mode now has Cinnamon's native radio dot and a “Selected:” label. The alternate choice says “Select:”. Both retain standard keyboard and mouse activation. Radio accessibility roles and Cinnamon's checked state expose selection to assistive technology. Selection updates after a successful controller response, and the existing 150 ms status refresh tracks changes from Settings. Offline status clears the selection; failed commands do not falsely mark a mode. Controller mode persistence already existed and is unchanged.

## Upgrade an existing v3.1 installation

Extract TapGuard-v3.1.1.zip. Open a terminal in its TapGuard folder and run without sudo:

```bash
bash upgrade-applet.sh
```

This backs up the installed applet beside its folder, then replaces only applet.js and metadata.json. It leaves the controller, saved mode/delay, pause behavior and autostart entry untouched. Log out and back in to reload Cinnamon's applet code. Existing enabled autostart will start the controller at login; if autostart is disabled, start it as you normally do.

For a new installation, follow README.md and run `bash install.sh`; that script intentionally enables autostart. The full installer/controller retain their original v3.1 wording because only the applet changes in this patch.

## Verify on your Cinnamon desktop

1. Open the menu: exactly one online mode should show its dot and “Selected:”.
2. Select the alternate mode with mouse, then keyboard (arrows and Enter/Space). Reopen the menu and check the selection. Tap-only preserves motion and physical clicks; full mode locks the trackpad while typing. Keep an external mouse available.
3. Change mode in Settings; confirm the panel menu follows it. Restart the controller or log out/in and confirm the saved choice remains.
4. Check countdown, pause/resume, Settings delay slider and existing login autostart.
5. Stop the controller: the panel should say Offline and neither mode should be marked selected. Start it again and confirm the selection returns.

## Rollback

Remove TapGuard from the panel. Copy applet.js and metadata.json from the backup path printed by the upgrade script into `~/.local/share/cinnamon/applets/tapguard@local/`. Log out/in and add TapGuard again. Saved controller settings are unaffected.

## Validation

Passed JavaScript syntax check, headless applet mode confirmation/exclusivity/failure/unknown-state checks, all seven existing mocked controller tests, Python compilation, and shell syntax checks. The controller source and original installer scripts are byte-for-byte unchanged. The native setShowDot API and its accessibility checked-state behavior were inspected in the installed Cinnamon source and upstream https://github.com/linuxmint/cinnamon/blob/master/js/ui/popupMenu.js.

This package has not been tested in the user's running Cinnamon environment. Theme rendering, keyboard/screen-reader behavior, hardware behavior and login persistence require the on-device verification above.
