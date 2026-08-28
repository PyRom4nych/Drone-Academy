from dataclasses import dataclass


@dataclass
class RecognizedPhrase:
    text: str
    timestamp: float


@dataclass
class Command:
    action: str
    params: dict
    source: str


@dataclass
class TargetState:
    throttle: float
    yaw: float
    pitch: float
    roll: float
    duration: float