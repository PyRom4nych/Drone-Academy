from shared_types import Command, TargetState
from dataclasses import dataclass

@dataclass
class ButtonCommand:
    button: str
    duration: float

class CommandMapper:
    def __init__(self, command_map: dict[str, dict], yaw_rate: float = 90):
        self.command_map = command_map
        self.yaw_rate = yaw_rate

    def map(self, cmd: Command) -> TargetState:
        action = cmd.action
        defaults = self.command_map.get(action, self.command_map.get("HOVER", {
            "throttle": 0.0, "yaw": 0.0, "pitch": 0.0, "roll": 0.0, "duration": 0.0
        }))

        angle = cmd.params.get("angle")
        duration = cmd.params.get("duration")
        yaw = defaults.get("yaw", 0.0)
        pitch = defaults.get("pitch", 0.0)
        roll = defaults.get("roll", 0.0)
        throttle = defaults.get("throttle", 0.0)

        if angle is not None and action in ("ROTATE_LEFT", "ROTATE_RIGHT"):
            base_speed = abs(yaw)
            speed = self.yaw_rate * base_speed / 0.5
            if duration is not None and duration > 0:
                required_speed = abs(angle) / duration
                yaw = (yaw / abs(yaw)) * (required_speed / self.yaw_rate * 0.5)
                final_duration = duration
            else:
                final_duration = abs(angle) / speed
            return TargetState(
                throttle=throttle,
                yaw=yaw,
                pitch=pitch,
                roll=roll,
                duration=final_duration
            )

        state = TargetState(
            throttle=throttle,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            duration=duration if duration is not None else defaults.get("duration", 0.0)
        )
        return state

    def map_button(self, cmd: Command) -> ButtonCommand | None:
        action = cmd.action
        mapping = self.command_map.get(action, {})
        if "button" in mapping:
            return ButtonCommand(
                button=mapping["button"],
                duration=float(cmd.params.get("duration", mapping.get("duration", 0.5)))
            )
        return None