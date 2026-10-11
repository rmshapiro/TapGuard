/* TapGuard v3 panel applet for Cinnamon 6.x (X11).
 * Displays controller status; no input handling takes place in Cinnamon.
 */
const Applet = imports.ui.applet;
const PopupMenu = imports.ui.popupMenu;
const Mainloop = imports.mainloop;
const GLib = imports.gi.GLib;
const Gio = imports.gi.Gio;
const Atk = imports.gi.Atk;
const ByteArray = imports.byteArray;

class TapGuardApplet extends Applet.TextIconApplet {
    constructor(metadata, orientation, panelHeight, instanceId) {
        super(orientation, panelHeight, instanceId);
        this._base = GLib.build_filenamev([GLib.get_home_dir(), '.cache', 'tapguard']);
        this._statusPath = GLib.build_filenamev([this._base, 'status.json']);
        this._script = GLib.build_filenamev([GLib.get_home_dir(), 'bin', 'tapguard.py']);
        this._lastStatus = null;
        this._timer = 0;
        this.set_applet_icon_symbolic_name('input-touchpad-symbolic');
        this.set_applet_label('TG …');
        this.set_applet_tooltip('TapGuard: waiting for controller');
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menuManager.addMenu(this.menu);

        this._toggleItem = new PopupMenu.PopupMenuItem('Pause / Resume');
        this._toggleItem.connect('activate', () => this._command(['--ctl', 'toggle']));
        this.menu.addMenuItem(this._toggleItem);

        this._modeItems = {};
        for (let mode of ['tap', 'full']) {
            let item = new PopupMenu.PopupMenuItem('');
            item.actor.accessible_role = Atk.Role.RADIO_MENU_ITEM;
            item.connect('activate', () => this._selectMode(mode));
            this._modeItems[mode] = item;
            this.menu.addMenuItem(item);
        }
        this._syncMode(null);

        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        let settings = new PopupMenu.PopupMenuItem('Settings / delay slider…');
        settings.connect('activate', () => this._command(['--gui']));
        this.menu.addMenuItem(settings);

        let start = new PopupMenu.PopupMenuItem('Start controller (if offline)');
        start.connect('activate', () => this._command(['--daemon']));
        this.menu.addMenuItem(start);

        this._update();
        this._timer = Mainloop.timeout_add(150, () => {
            this._update();
            return true;
        });
    }

    _syncMode(mode) {
        for (let value of ['tap', 'full']) {
            let selected = mode === value;
            let description = value === 'tap' ? 'Block taps only' : 'Full trackpad lockout';
            this._modeItems[value].setShowDot(selected);
            this._modeItems[value].label.set_text(
                (selected ? 'Selected: ' : 'Select: ') + description);
        }
    }

    _selectMode(mode) {
        try {
            let process = Gio.Subprocess.new(
                ['/usr/bin/python3', this._script, '--ctl', 'mode', mode],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            process.communicate_utf8_async(null, null, (source, result) => {
                try {
                    let [ok, stdout, stderr] = source.communicate_utf8_finish(result);
                    if (!ok || !source.get_successful())
                        throw new Error(stderr || 'Mode command failed');
                    let answer = JSON.parse(stdout);
                    if (!answer.ok) throw new Error(answer.error || 'Mode rejected');
                    // Mark only the controller-confirmed mode, never an optimistic choice.
                    if (!this._removed) this._syncMode(answer.mode);
                } catch (error) {
                    global.logError(error);
                    if (!this._removed) this._update();
                }
            });
        } catch (error) {
            global.logError(error);
            this._update();
        }
    }

    _command(args) {
        try {
            GLib.spawn_async(null,
                ['/usr/bin/python3', this._script].concat(args),
                null, GLib.SpawnFlags.SEARCH_PATH, null);
        } catch (error) {
            global.logError(error);
        }
    }

    _update() {
        try {
            let [ok, bytes] = GLib.file_get_contents(this._statusPath);
            if (!ok) throw new Error('No controller status');
            let s = JSON.parse(ByteArray.toString(bytes));
            if (!s.timestamp || (Date.now() / 1000) - s.timestamp > 3.0)
                throw new Error('Controller not responding');
            this._lastStatus = s;
            this._syncMode(s.mode);
            let label;
            if (!s.enabled)
                label = 'TG Paused';
            else if (s.locked)
                label = 'TG ' + Number(s.remaining).toFixed(1) + 's';
            else
                label = 'TG Ready';
            this.set_applet_label(label);
            this.set_applet_tooltip('TapGuard: ' +
                (s.mode === 'full' ? 'Full lockout' : 'Tap-only') +
                ' / ' + Number(s.delay).toFixed(1) + 's delay' +
                (s.enabled ? '' : ' (paused)'));
            this._toggleItem.label.set_text(s.enabled ? 'Pause protection' : 'Resume protection');
        } catch (error) {
            this._lastStatus = null;
            this._syncMode(null);
            this.set_applet_label('TG Offline');
            this.set_applet_tooltip('TapGuard controller is not running');
            this._toggleItem.label.set_text('Pause / Resume');
        }
    }

    on_applet_clicked(event) {
        this._update();
        this.menu.toggle();
    }

    on_applet_removed_from_panel() {
        this._removed = true;
        if (this._timer) {
            Mainloop.source_remove(this._timer);
            this._timer = 0;
        }
    }
}

function main(metadata, orientation, panelHeight, instanceId) {
    return new TapGuardApplet(metadata, orientation, panelHeight, instanceId);
}
