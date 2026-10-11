// Headless behavior checks; does not render Cinnamon widgets.
const assert = require('assert');
const vm = require('vm');
const fs = require('fs');
let callback;
const context = { imports: {ui: {applet: {TextIconApplet: class {}}, popupMenu: {}}, mainloop: {}, byteArray: {}, gi: {GLib: {}, Atk: {}, Gio: {SubprocessFlags: {STDOUT_PIPE: 1, STDERR_PIPE: 2}, Subprocess: {new(argv) { assert.deepEqual(Array.from(argv).slice(-3), ['--ctl', 'mode', 'tap']); return {communicate_utf8_async(a,b,cb) {callback=cb;}}; }}}}}, global: {logError() {}}, Date };
vm.createContext(context);
vm.runInContext(fs.readFileSync('cinnamon/tapguard@local/applet.js','utf8') + '\nthis.AppletClass = TapGuardApplet;',context);
const app = Object.create(context.AppletClass.prototype);
function item() {return {setShowDot(v) {this.dot=v;}, label: {set_text(v) {this.text=v;}}};}
app._modeItems = {tap:item(), full:item()};
app._script = '/test/tapguard.py';
app._syncMode('full');
assert.equal(app._modeItems.full.dot,true);
assert.equal(app._modeItems.tap.label.text,'Select: Block taps only');
app._selectMode('tap');
assert.equal(app._modeItems.full.dot,true); // Wait for confirmation.
callback({communicate_utf8_finish() {return [true, '{"ok":true,"mode":"tap"}', ''];}, get_successful() {return true;}}, {});
assert.equal(app._modeItems.tap.dot,true);
assert.equal(app._modeItems.full.dot,false);
let refreshed=false;
app._update=()=>{refreshed=true;};
app._selectMode('tap');
callback({communicate_utf8_finish() {return [true, '', 'offline'];}, get_successful() {return false;}}, {});
assert.equal(refreshed,true);
app._syncMode(null);
assert.equal(app._modeItems.tap.dot,false);
assert.equal(app._modeItems.full.dot,false);
console.log('Applet mode confirmation, exclusivity, failure and unknown-state checks passed.');
