import time
import threading
from queue import Queue, Empty

from vgamepad import VX360Gamepad, XUSB_BUTTON
from shared_types import TargetState


class ControlLayer:
    def __init__(self, config, priority_queue: Queue):
        self.priority_queue = priority_queue
        self.hz = config.control_loop_hz
        self._pad = VX360Gamepad()
        self._current_target = TargetState(throttle=0.0, yaw=0.0, pitch=0.0, roll=0.0, duration=0.0)
        self._current_axes = {"throttle": 0.0, "yaw": 0.0, "pitch": 0.0, "roll": 0.0}
        self._deadline = 0.0
        self._running = threading.Event()
        self._thread = None

    def start(self):
        self._running.set()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=1.0)

    def set_target(self, state: TargetState):
        self._current_target = state
        self._deadline = time.monotonic() + state.duration if state.duration > 0 else 0.0

    def emergency_stop(self):
        self._current_target = TargetState(throttle=0.0, yaw=0.0, pitch=0.0, roll=0.0, duration=0.0)
        self._deadline = 0.0
        self._current_axes = {"throttle": 0.0, "yaw": 0.0, "pitch": 0.0, "roll": 0.0}
        self._apply_axes()

    def press_button(self, button: str, duration: float = 0.1):
        button_map = {
            'X': XUSB_BUTTON.XUSB_GAMEPAD_X,
            'Y': XUSB_BUTTON.XUSB_GAMEPAD_Y,
        }
        btn = button_map.get(button.upper())
        if btn is None:
            return
        self._pad.press_button(btn)
        self._pad.update()
        time.sleep(duration)
        self._pad.release_button(btn)
        self._pad.update()

    def _loop(self):
        period = 1.0 / self.hz
        lerp_factor = 0.3
        while self._running.is_set():
            frame_start = time.monotonic()
            self._process_priority()
            self._update_target()
            self._interpolate(lerp_factor)
            self._apply_axes()
            elapsed = time.monotonic() - frame_start
            sleep_time = period - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _process_priority(self):
        try:
            cmd = self.priority_queue.get_nowait()
            if cmd.action == "EMERGENCY_STOP":
                self.emergency_stop()
        except Empty:
            pass

    def _update_target(self):
        if self._deadline and time.monotonic() >= self._deadline:
            self._current_target = TargetState(throttle=0.0, yaw=0.0, pitch=0.0, roll=0.0, duration=0.0)
            self._deadline = 0.0

    def _interpolate(self, factor):
        for axis in ("throttle", "yaw", "pitch", "roll"):
            target_val = getattr(self._current_target, axis)
            self._current_axes[axis] += (target_val - self._current_axes[axis]) * factor

    def _apply_axes(self):
        self._pad.left_joystick_float(x_value_float=self._current_axes["yaw"],
                                      y_value_float=self._current_axes["throttle"])
        self._pad.right_joystick_float(x_value_float=self._current_axes["roll"],
                                       y_value_float=self._current_axes["pitch"])
        self._pad.update()