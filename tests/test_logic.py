"""Run with: python3 -m unittest discover -s tests -v"""
import importlib.util
from pathlib import Path
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / "tapguard.py"
spec = importlib.util.spec_from_file_location("tapguard_v3", path)
tapguard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tapguard)


class TimingTests(unittest.TestCase):
    def test_countdown(self):
        self.assertAlmostEqual(tapguard.seconds_remaining(100, 100.5, 1.5), 1.0)
        self.assertEqual(tapguard.seconds_remaining(100, 200, 1.5), 0)
        self.assertEqual(tapguard.seconds_remaining(0, 100, 1.5), 0)

    def test_limits_and_invalid_delay(self):
        for raw, expected in [("0", 0.5), ("9", 5.0), ("1.54", 1.5),
                              ("nan", 1.5), ("hello", 1.5)]:
            self.assertEqual(tapguard.clamp_delay(raw), expected)


class ControllerTests(unittest.TestCase):
    def setUp(self):
        with patch.object(tapguard, "read_config", return_value={"mode": "full", "delay": 1.5}):
            self.controller = tapguard.Controller()
        self.events = []
        def dummy_input(*args):
            self.events.append(args)
            return ""
        self.patcher = patch.object(tapguard, "run_xinput", side_effect=dummy_input)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_full_lockout_and_timeout(self):
        with patch.object(tapguard.time, "monotonic", return_value=101):
            self.controller.last_key = 100.0
            self.controller.apply_state()
        self.assertFalse(self.controller.current_device_enabled)
        self.assertIn(("disable", "Apple SPI Touchpad"), self.events)
        with patch.object(tapguard.time, "monotonic", return_value=102):
            self.controller.apply_state()
        self.assertTrue(self.controller.current_device_enabled)
        self.assertIn(("enable", "Apple SPI Touchpad"), self.events)

    def test_tap_only_and_pause_restores(self):
        self.controller.config["mode"] = "tap"
        with patch.object(tapguard.time, "monotonic", return_value=101):
            self.controller.last_key = 100.0
            self.controller.apply_state()
        self.assertEqual(self.controller.current_tap, 0)
        self.assertTrue(self.controller.current_device_enabled)
        self.controller.apply_command({"command": "pause"})
        self.assertEqual(self.controller.current_tap, 1)
        self.assertTrue(self.controller.current_device_enabled)
        self.assertFalse(self.controller.enabled)

    def test_switch_full_to_tap_during_lock(self):
        self.controller.last_key = 100
        with patch.object(tapguard.time, "monotonic", return_value=100.4):
            self.controller.apply_state()
            self.assertFalse(self.controller.current_device_enabled)
            with patch.object(tapguard, "save_config"):
                self.controller.apply_command({"command": "mode", "value": "tap"})
            self.assertTrue(self.controller.current_device_enabled)
            self.assertEqual(self.controller.current_tap, 0)


class RecoveryTests(unittest.TestCase):
    def test_tapping_recovery_attempted_after_enable_failure(self):
        with patch.object(tapguard, "run_xinput", side_effect=[OSError("device unavailable"), ""]) as command:
            with self.assertRaises(OSError):
                tapguard.restore_touchpad()
        self.assertEqual(command.call_args_list[-1].args,
                         ("set-prop", "Apple SPI Touchpad", "libinput Tapping Enabled", "1"))

    def test_wayland_refused_before_supervisor_starts(self):
        with patch.object(tapguard.sys, "argv", ["tapguard.py", "--daemon"]), \
             patch.dict(tapguard.os.environ, {"XDG_SESSION_TYPE": "wayland", "DISPLAY": ":0"}), \
             patch.object(tapguard, "supervise") as supervisor:
            with self.assertRaisesRegex(RuntimeError, "X11"):
                tapguard.main()
            supervisor.assert_not_called()


if __name__ == "__main__":
    unittest.main()

class PalmControllerTests(ControllerTests):
    def setUp(self):
        super().setUp()
        self.controller.original_dwt = 1
        self.controller.current_dwt = 1
        self.controller.config['mode'] = 'palm'
        self.state = dict(ready=True, palm=False, error='', generation=1)
        self.sensor = patch.object(self.controller.palm, 'snapshot', side_effect=lambda: dict(self.state))
        self.sensor.start()

    def tearDown(self):
        self.sensor.stop()
        super().tearDown()

    # Override inherited typing checks: those are independently tested above.
    def test_full_lockout_and_timeout(self):
        self.state['palm'] = True
        self.controller.last_key = 0
        self.controller.apply_state()
        self.assertFalse(self.controller.current_device_enabled)
        self.assertEqual(self.controller.current_dwt, 0)
        self.assertTrue(self.controller.status()['locked'])
        self.assertEqual(self.controller.status()['remaining'], 0)
        self.state['palm'] = False
        self.controller.last_key = tapguard.time.monotonic()
        self.controller.apply_state()
        self.assertTrue(self.controller.current_device_enabled)  # Typing has no effect.

    def test_tap_only_and_pause_restores(self):
        self.state['palm'] = True
        self.controller.apply_state()
        self.controller.apply_command({'command':'pause'})
        self.assertTrue(self.controller.current_device_enabled)
        self.assertEqual(self.controller.current_dwt, 1)
        self.controller.apply_command({'command':'resume'})
        self.controller.apply_state()
        self.assertFalse(self.controller.current_device_enabled)

    def test_switch_full_to_tap_during_lock(self):
        self.state['palm'] = True
        self.controller.apply_state()
        with patch.object(tapguard,'save_config') as save:
            self.controller.apply_command({'command':'mode','value':'tap'})
            save.assert_called_once()
        self.assertTrue(self.controller.current_device_enabled)
        self.assertEqual(self.controller.current_dwt, 1)

    def test_sensor_loss_restores_and_reconnect_relocks(self):
        self.state['palm'] = True
        self.controller.apply_state()
        self.state.update(ready=False,palm=False,error='disconnected')
        self.controller.apply_state()
        self.assertTrue(self.controller.current_device_enabled)
        self.assertEqual(self.controller.current_dwt,1)
        self.state.update(ready=True,palm=True,generation=2,error='')
        self.controller.apply_state()
        self.assertFalse(self.controller.current_device_enabled)

    def test_unavailable_mode_does_not_persist(self):
        self.controller.config['mode']='full'
        self.state['ready']=False
        with patch.object(tapguard,'save_config') as save:
            result=self.controller.apply_command({'command':'mode','value':'palm'})
            self.assertFalse(result['ok'])
            save.assert_not_called()
        self.assertEqual(self.controller.config['mode'],'full')

    def test_original_disabled_dwt_is_preserved(self):
        self.controller.original_dwt=0
        self.controller.current_dwt=0
        self.state['palm']=True
        self.controller.apply_state()
        self.controller.apply_command({'command':'pause'})
        self.assertEqual(self.controller.current_dwt,0)
