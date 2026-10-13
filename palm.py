"""Read only Apple SPI Touchpad contact size; never grabs input or reads keys."""
import array
import fcntl
import select
import threading
import time

DEVICE = 'Apple SPI Touchpad'

class Contacts:
    def __init__(self, threshold=1600):
        self.threshold = threshold
        self.slot = 0
        self.slots = {}

    def update(self, code, value):
        if code == 47:
            self.slot = value
        elif code == 57:
            self.slots[self.slot] = {'id': value, 'major': 0, 'palm': False}
        elif code == 48:
            s = self.slots.setdefault(self.slot, {'id': -1, 'major': 0, 'palm': False})
            s['major'] = value
            if s['id'] >= 0 and value >= self.threshold:
                s['palm'] = True

    def report(self):
        active = [s for s in self.slots.values() if s['id'] >= 0]
        return {'palm': any(s['palm'] for s in active), 'contacts': len(active)}

class PalmMonitor:
    def __init__(self, threshold=1600):
        self.threshold = threshold
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.state = {'palm': False, 'contacts': 0, 'ready': False,
                      'error': 'Palm reader starting', 'heartbeat': 0, 'generation': 0}
        self.thread = None

    def publish(self, **values):
        with self.lock:
            self.state.update(values)

    def snapshot(self):
        with self.lock:
            result = dict(self.state)
        if time.monotonic() - result['heartbeat'] > 1:
            result.update(ready=False, palm=False, error='Palm reader unavailable')
        return result

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)

    def run(self):
        while not self.stop.is_set():
            try:
                from evdev import InputDevice, list_devices, ecodes
                dev = None
                for node in list_devices():
                    candidate = InputDevice(node)
                    if candidate.name == DEVICE:
                        dev = candidate
                        break
                    candidate.close()
                if dev is None:
                    raise RuntimeError('Touchpad unreadable; run enable-palm-access.sh')
                try:
                    axes = {code for code, _ in dev.capabilities().get(ecodes.EV_ABS, [])}
                    if not {47, 48, 57}.issubset(axes):
                        raise RuntimeError('Touchpad lacks multitouch size/slot data')
                    state = Contacts(self.threshold)
                    def resync():
                        count = dev.absinfo(47).max + 1
                        if not 1 <= count <= 128:
                            raise RuntimeError('Unexpected touchpad slot count')
                        values = {}
                        for code in (57, 48):
                            buf = array.array('i', [code] + [0] * count)
                            fcntl.ioctl(dev.fd, 0x8000450a | (len(buf) * buf.itemsize << 16), buf, True)
                            values[code] = buf[1:]
                        # Preserve palm classification for unchanged tracking IDs after dropped events.
                        old = state.slots
                        state.slots = {}
                        for slot in range(count):
                            state.update(47, slot)
                            state.update(57, values[57][slot])
                            state.update(48, values[48][slot])
                            if old.get(slot, {}).get('id') == values[57][slot] and old[slot]['palm']:
                                state.slots[slot]['palm'] = True
                        state.slot = dev.absinfo(47).value
                    resync()
                    with self.lock:
                        self.state['generation'] += 1
                    dropped = False
                    while not self.stop.is_set():
                        ready, _, _ = select.select([dev.fd], [], [], .1)
                        if ready:
                            for ev in dev.read():
                                if ev.type == ecodes.EV_SYN and ev.code == ecodes.SYN_DROPPED:
                                    dropped = True
                                    self.publish(ready=False, palm=False, error='Resynchronizing contacts')
                                elif ev.type == ecodes.EV_SYN and ev.code == ecodes.SYN_REPORT:
                                    if dropped:
                                        resync()
                                        dropped = False
                                    self.publish(**state.report(), ready=True, error='', heartbeat=time.monotonic())
                                elif ev.type == ecodes.EV_ABS and not dropped:
                                    state.update(ev.code, ev.value)
                        if not dropped:
                            self.publish(**state.report(), ready=True, error='', heartbeat=time.monotonic())
                finally:
                    dev.close()
            except Exception as exc:
                self.publish(ready=False, palm=False, contacts=0, error=str(exc), heartbeat=time.monotonic())
                self.stop.wait(1)
