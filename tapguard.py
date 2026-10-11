#!/usr/bin/env python3
"""TapGuard v3.1: timed X11 touchpad suppression, Cinnamon panel + Tk controls.

Requires an X11 session, xinput, and (for the GUI) python3-tk.
No root access and no keyboard content is recorded.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import queue
import re
import signal
import socket
import subprocess
import sys
import threading
import time

DEVICE = "Apple SPI Touchpad"
TAPPING_PROP = "libinput Tapping Enabled"
BASE = Path.home() / ".cache" / "tapguard"
CONFIG_PATH = Path.home() / ".config" / "tapguard.json"  # reuse v2 settings
STATUS_PATH = BASE / "status.json"
SOCKET_PATH = BASE / "control.sock"
LOCK_PATH = BASE / "daemon.lock"
LOG_PATH = BASE / "tapguard.log"
DEFAULT_DELAY = 1.5
DEFAULT_MODE = "full"  # latest proven configuration; saved v2 choice takes precedence
POLL = 0.075


def run_xinput(*args: str) -> str:
    return subprocess.run(["xinput", *args], check=True, text=True,
                          capture_output=True, timeout=5).stdout


def read_property(name: str) -> int:
    text = run_xinput("list-props", DEVICE)
    match = re.search(r"^\s*" + re.escape(name) +
                      r" \(\d+\):\s*([01])\s*$", text, re.MULTILINE)
    if not match:
        raise RuntimeError(f"Cannot read '{name}' from {DEVICE}")
    return int(match.group(1))


def clamp_delay(value) -> float:
    try:
        number = float(value)
        if number != number:  # NaN
            raise ValueError("NaN")
        return round(max(0.5, min(5.0, number)), 1)
    except (ValueError, TypeError, OverflowError):
        return DEFAULT_DELAY


def read_config() -> dict:
    try:
        settings = json.loads(CONFIG_PATH.read_text())
        if not isinstance(settings, dict):
            settings = {}
    except (OSError, ValueError):
        settings = {}
    return {
        "delay": clamp_delay(settings.get("delay", DEFAULT_DELAY)),
        "mode": settings.get("mode") if settings.get("mode") in ("tap", "full") else DEFAULT_MODE,
    }


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = CONFIG_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(CONFIG_PATH)


def write_status(status: dict) -> None:
    BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = STATUS_PATH.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(status, separators=(",", ":")))
    temporary.replace(STATUS_PATH)


def restore_touchpad() -> None:
    """Failsafe: return Apple touchpad to usable state with tap-to-click ON.

    The user's desired normal setting is tap-to-click enabled, not the transient
    state found when a prior TapGuard process happened to be killed.
    """
    try:
        run_xinput("enable", DEVICE)
    finally:
        run_xinput("set-prop", DEVICE, TAPPING_PROP, "1")


def seconds_remaining(last_key: float, now: float, delay: float) -> float:
    if last_key <= 0:
        return 0.0
    return max(0.0, delay - (now - last_key))


class Controller:
    def __init__(self):
        self.config = read_config()
        self.enabled = True
        self.last_key = 0.0
        self.current_tap = 1
        self.current_device_enabled = True
        self.stop_event = threading.Event()
        self.monitor_lost = False
        self.requests: queue.Queue = queue.Queue(maxsize=16)
        self.sock: socket.socket | None = None
        self.monitor: subprocess.Popen | None = None

    def keyboard_reader(self):
        try:
            assert self.monitor and self.monitor.stdout
            for line in self.monitor.stdout:
                if "RawKeyPress" in line:
                    self.last_key = time.monotonic()
                if self.stop_event.is_set():
                    return
        except Exception as exc:
            print("Keyboard monitor error:", exc, file=sys.stderr, flush=True)
        self.monitor_lost = True

    def socket_reader(self):
        assert self.sock
        while not self.stop_event.is_set():
            try:
                client, _ = self.sock.accept()
                client.settimeout(2)
                # A bounded protocol. The socket is created 0600 and local-only.
                payload = client.recv(4096)
                request = json.loads(payload.decode("utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("Expected a JSON object")
                self.requests.put_nowait((request, client))
            except socket.timeout:
                continue
            except (OSError, ValueError, queue.Full) as exc:
                if not self.stop_event.is_set():
                    print("Socket request ignored:", exc, file=sys.stderr, flush=True)
                try:
                    client.close()
                except (UnboundLocalError, OSError):
                    pass

    def apply_command(self, request: dict) -> dict:
        command = request.get("command")
        if command == "status":
            pass
        elif command == "pause":
            self.enabled = False
            self.last_key = 0.0
            self.restore()
        elif command == "resume":
            self.enabled = True
            self.last_key = 0.0
        elif command == "stop":
            self.enabled = False
            self.restore()
            self.stop_event.set()
        elif command == "toggle":
            self.enabled = not self.enabled
            self.last_key = 0.0
            if not self.enabled:
                self.restore()
        elif command == "mode":
            mode = request.get("value")
            if mode not in ("tap", "full"):
                return {"ok": False, "error": "Unknown mode"}
            self.config["mode"] = mode
            save_config(self.config)
            # Transition from full -> tap while locked must reenable the device.
            self.apply_state()
        elif command == "delay":
            self.config["delay"] = clamp_delay(request.get("value"))
            save_config(self.config)
        else:
            return {"ok": False, "error": "Unknown command"}
        return {"ok": True, **self.status()}

    def set_device(self, enabled: bool):
        if self.current_device_enabled != enabled:
            run_xinput("enable" if enabled else "disable", DEVICE)
            self.current_device_enabled = enabled

    def set_tapping(self, enabled: bool):
        value = int(enabled)
        if self.current_tap != value:
            run_xinput("set-prop", DEVICE, TAPPING_PROP, str(value))
            self.current_tap = value

    def restore(self):
        # Enable first so even a subsequent error does not strand the pointer.
        self.set_device(True)
        self.set_tapping(True)

    def status(self):
        remaining = (seconds_remaining(self.last_key, time.monotonic(),
                                       self.config["delay"]) if self.enabled else 0.0)
        return {
            "timestamp": time.time(),
            "enabled": self.enabled,
            "mode": self.config["mode"],
            "delay": self.config["delay"],
            "remaining": round(remaining, 2),
            "locked": self.enabled and remaining > 0,
            "device_enabled": self.current_device_enabled,
        }

    def apply_state(self):
        remaining = seconds_remaining(self.last_key, time.monotonic(),
                                      self.config["delay"]) if self.enabled else 0
        if remaining > 0:
            if self.config["mode"] == "full":
                self.set_device(False)
            else:
                self.set_device(True)
                self.set_tapping(False)
        else:
            self.restore()

    def serve(self):
        BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Never start unless the device can be read; clean stale v2 tap state.
        read_property("Device Enabled")
        read_property(TAPPING_PROP)
        restore_touchpad()
        self.monitor = subprocess.Popen(
            ["stdbuf", "-oL", "xinput", "test-xi2", "--root"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, bufsize=1)
        threading.Thread(target=self.keyboard_reader, daemon=True).start()
        if SOCKET_PATH.exists():
            SOCKET_PATH.unlink()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.bind(str(SOCKET_PATH))
        os.chmod(SOCKET_PATH, 0o600)
        self.sock.listen(4)
        self.sock.settimeout(.25)
        threading.Thread(target=self.socket_reader, daemon=True).start()
        try:
            while not self.stop_event.is_set():
                if self.monitor_lost or self.monitor.poll() is not None:
                    raise RuntimeError("Keyboard monitor stopped; restoring touchpad")
                while True:
                    try:
                        request, client = self.requests.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        response = self.apply_command(request)
                        client.sendall(json.dumps(response).encode())
                    except Exception as exc:
                        try:
                            client.sendall(json.dumps({"ok": False, "error": str(exc)}).encode())
                        except OSError:
                            pass
                    finally:
                        client.close()
                self.apply_state()
                write_status(self.status())
                time.sleep(POLL)
        finally:
            self.stop_event.set()
            # Force a real recovery command even if cached state is stale.
            try:
                restore_touchpad()
            except Exception as exc:
                print("Controller restore failed:", exc, file=sys.stderr, flush=True)
            if self.sock:
                self.sock.close()
            if self.monitor and self.monitor.poll() is None:
                self.monitor.terminate()
                try:
                    self.monitor.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.monitor.kill()
            try:
                SOCKET_PATH.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                STATUS_PATH.unlink(missing_ok=True)
            except OSError:
                pass


def supervise():
    """Parent watchdog restores input even if the controller crashes."""
    BASE.mkdir(parents=True, exist_ok=True, mode=0o700)
    def request_stop(_signal, _frame):
        if worker is not None and worker.poll() is None:
            worker.terminate()

    worker = None
    previous_term = signal.signal(signal.SIGTERM, request_stop)
    previous_int = signal.signal(signal.SIGINT, request_stop)
    with LOCK_PATH.open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("TapGuard is already running")
            return 0
        try:
            with LOG_PATH.open("a") as log:
                worker = subprocess.Popen(
                    [sys.executable, str(Path(__file__).resolve()), "--worker"],
                    stdout=log, stderr=log)
                print(f"TapGuard supervisor started (worker PID {worker.pid})", flush=True)
                return worker.wait()
        finally:
            if worker is not None and worker.poll() is None:
                worker.terminate()
                try:
                    worker.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    worker.kill()
                    worker.wait()
            # Last-resort cleanup after child exits unexpectedly.
            try:
                restore_touchpad()
            except Exception as exc:
                print("Failsafe restore failed:", exc, file=sys.stderr)
            signal.signal(signal.SIGTERM, previous_term)
            signal.signal(signal.SIGINT, previous_int)


def control(command: str, value=None, *, timeout=2.5) -> dict:
    request = {"command": command}
    if value is not None:
        request["value"] = value
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect(str(SOCKET_PATH))
        s.sendall(json.dumps(request).encode())
        received = s.recv(4096)
    return json.loads(received.decode("utf-8"))


def launch_gui():
    import tkinter as tk
    from tkinter import ttk

    window = tk.Tk()
    window.title("TapGuard v3.1 Settings")
    window.geometry("470x385")
    window.minsize(410, 345)
    window.resizable(True, True)
    frm = ttk.Frame(window, padding=18)
    frm.pack(fill="both", expand=True)
    ttk.Label(frm, text="TapGuard", font=("Sans", 17, "bold")).pack(anchor="w")
    ttk.Label(frm, text="Typing protection for the Apple SPI Touchpad").pack(anchor="w", pady=(0, 10))

    cfg = read_config()
    mode = tk.StringVar(value=cfg["mode"])
    delay = tk.DoubleVar(value=cfg["delay"])
    status = tk.StringVar(value="Connecting…")
    countdown = tk.StringVar(value="")

    row = ttk.LabelFrame(frm, text="Protection mode", padding=8)
    row.pack(fill="x", pady=7)
    for text, val in (("Block entire trackpad", "full"),
                      ("Block taps only", "tap")):
        ttk.Radiobutton(row, text=text, value=val, variable=mode,
                        command=lambda: send("mode", mode.get())).pack(anchor="w")

    # Keep the value visible while moving the slider.  Do not let the
    # 250-ms status refresh overwrite the thumb position mid-drag.
    delay_display = tk.StringVar(value=f"Delay after typing: {delay.get():.1f} seconds")
    delay.trace_add("write", lambda *_: delay_display.set(
        f"Delay after typing: {delay.get():.1f} seconds"))
    delay_label = ttk.Label(frm, textvariable=delay_display)
    delay_label.pack(anchor="w", pady=(12, 0))
    scale = ttk.Scale(frm, from_=0.5, to=5.0, variable=delay)
    scale.pack(fill="x", pady=(2, 9))
    dragging = False

    def begin_drag(event):
        nonlocal dragging
        dragging = True

    def finish_drag(event):
        nonlocal dragging
        dragging = False
        set_delay()

    scale.bind("<ButtonPress-1>", begin_drag)
    scale.bind("<ButtonRelease-1>", finish_drag)
    scale.bind("<KeyRelease>", lambda event: set_delay())

    def set_delay():
        adjusted = clamp_delay(delay.get())
        delay.set(adjusted)
        send("delay", adjusted)

    def send(action, value=None):
        try:
            answer = control(action, value)
            if not answer.get("ok"):
                status.set(answer.get("error", "Command rejected"))
        except (OSError, ValueError) as exc:
            status.set(f"Controller unavailable: {exc}")

    ttk.Label(frm, textvariable=countdown, font=("Sans", 13, "bold")).pack(pady=(8, 0))
    ttk.Label(frm, textvariable=status).pack(pady=3)
    buttons = ttk.Frame(frm)
    buttons.pack(pady=12)
    pause_button = ttk.Button(buttons, text="Pause / Resume", command=lambda: send("toggle"))
    pause_button.pack(side="left", padx=5)
    ttk.Button(buttons, text="Close", command=window.destroy).pack(side="left", padx=5)

    def refresh():
        if not window.winfo_exists():
            return
        try:
            answer = control("status", timeout=.35)
            if not answer.get("ok"):
                raise OSError("Controller rejected request")
            remaining = answer["remaining"]
            is_enabled = answer["enabled"]
            countdown.set(f"{remaining:.1f}s remaining" if remaining > 0 else
                          ("Ready" if is_enabled else "Paused"))
            status.set(("Full lockout" if answer["mode"] == "full" else "Tap-only")
                       + (" • running" if is_enabled else " • paused"))
            if not dragging:
                delay.set(answer["delay"])
            mode.set(answer["mode"])
        except (OSError, ValueError, KeyError):
            countdown.set("Offline")
            status.set("Start the TapGuard background controller")
        window.after(250, refresh)

    refresh()
    window.mainloop()


def main():
    parser = argparse.ArgumentParser(description="TapGuard v3")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--daemon", action="store_true", help="supervisor + controller, for autostart")
    action.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    action.add_argument("--gui", action="store_true", help="Tk settings window")
    action.add_argument("--ctl", nargs="+", metavar="ARG", help="status, toggle, pause, resume, stop, mode tap|full, delay N")
    args = parser.parse_args()
    if args.daemon or args.worker:
        if os.environ.get("XDG_SESSION_TYPE") != "x11" or not os.environ.get("DISPLAY"):
            raise RuntimeError("TapGuard requires a desktop X11 session; Wayland is unsupported")
        os.umask(0o077)
    if args.daemon:
        return supervise()
    if args.worker:
        controller = Controller()
        def stop(_sig, _frame):
            controller.stop_event.set()
        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        controller.serve()
        return 0
    if args.gui:
        launch_gui()
        return 0
    if args.ctl:
        name, *values = args.ctl
        if name in ("mode", "delay") and len(values) == 1:
            answer = control(name, values[0])
        elif name in ("status", "toggle", "pause", "resume", "stop") and not values:
            answer = control(name)
        else:
            parser.error("Usage: --ctl status|toggle|pause|resume|stop|mode tap|full|delay 1.5")
        print(json.dumps(answer, indent=2))
        return 0 if answer.get("ok") else 1
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"TapGuard: {exc}", file=sys.stderr)
        raise SystemExit(1)
