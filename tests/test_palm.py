import unittest
from palm import Contacts, PalmMonitor

class ContactTests(unittest.TestCase):
    def touch(self, s, slot, identity, size):
        s.update(47, slot)
        s.update(57, identity)
        s.update(48, size)

    def test_finger_does_not_lock(self):
        s = Contacts(); self.touch(s, 0, 1, 1000)
        self.assertFalse(s.report()['palm'])

    def test_palm_and_finger_remain_locked(self):
        s = Contacts(); self.touch(s, 0, 1, 4200); self.touch(s, 1, 2, 700)
        self.assertEqual(s.report()['contacts'], 2)
        self.assertTrue(s.report()['palm'])
        s.update(57, -1)  # Lift finger, not palm.
        self.assertTrue(s.report()['palm'])

    def test_palm_lift_unlocks_even_if_finger_stays(self):
        s = Contacts(); self.touch(s, 0, 1, 4200); self.touch(s, 1, 2, 700)
        s.update(47, 0); s.update(57, -1)
        self.assertFalse(s.report()['palm'])
        self.assertEqual(s.report()['contacts'], 1)

    def test_size_drop_does_not_unclassify_existing_palm(self):
        s = Contacts(); self.touch(s, 0, 1, 4200); s.update(48, 800)
        self.assertTrue(s.report()['palm'])

    def test_reused_slot_does_not_keep_old_palm(self):
        s = Contacts(); self.touch(s, 0, 1, 4200); self.touch(s, 0, 2, 800)
        self.assertFalse(s.report()['palm'])

    def test_second_palm_keeps_lock(self):
        s = Contacts(); self.touch(s, 0, 1, 4200); self.touch(s, 1, 2, 4200)
        s.update(47, 0); s.update(57, -1)
        self.assertTrue(s.report()['palm'])

if __name__ == '__main__': unittest.main()

class MonitorTests(unittest.TestCase):
    def test_stale_reader_fails_open(self):
        m = PalmMonitor()
        m.publish(ready=True, palm=True, heartbeat=0)
        s = m.snapshot()
        self.assertFalse(s['ready'])
        self.assertFalse(s['palm'])

    def test_reader_error_is_visible(self):
        import time
        m = PalmMonitor()
        m.publish(ready=False, palm=False, error='No access', heartbeat=time.monotonic())
        self.assertEqual(m.snapshot()['error'], 'No access')

class ReaderIntegrationTests(unittest.TestCase):
    def test_evdev_reader_tracks_palm_plus_finger_and_closes(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        m = PalmMonitor()
        closed = []
        def read():
            m.stop.set()
            return [SimpleNamespace(type=3,code=47,value=1),
                    SimpleNamespace(type=3,code=57,value=20),
                    SimpleNamespace(type=3,code=48,value=700),
                    SimpleNamespace(type=0,code=0,value=0)]
        dev = SimpleNamespace(name='Apple SPI Touchpad',fd=99,
            capabilities=lambda:{3:[(47,None),(48,None),(57,None)]},
            absinfo=lambda code: SimpleNamespace(max=1,value=0),read=read,
            close=lambda:closed.append(True))
        def ioctl(fd, request, buf, mutate):
            buf[1:] = __import__('array').array('i', [10,-1] if buf[0]==57 else [4200,0])
        fake = SimpleNamespace(InputDevice=lambda node:dev,list_devices=lambda:['/fake/touchpad'],
            ecodes=SimpleNamespace(EV_ABS=3,EV_SYN=0,SYN_REPORT=0,SYN_DROPPED=3))
        with patch.dict('sys.modules',{'evdev':fake}), patch('palm.fcntl.ioctl',side_effect=ioctl), \
             patch('palm.select.select',return_value=([99],[],[])):
            m.run()
        self.assertTrue(m.snapshot()['ready'])
        self.assertTrue(m.snapshot()['palm'])
        self.assertEqual(m.snapshot()['contacts'],2)
        self.assertEqual(closed,[True])
