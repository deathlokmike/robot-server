from dataclasses import dataclass
from enum import Enum

from starlette.websockets import WebSocket


class ConnectionType(Enum):
    robot = 0
    client = 1


class RobotStatus(Enum):
    launched = "start"
    stopped = "stop"

    suspended = "suspend"
    resumed = "resume"
    checked_system = "check_system"
    checked_camera = "check_camera"
    remote_forward = "remote_forward"
    remote_backward = "remote_backward"
    remote_left = "remote_left"
    remote_right = "remote_right"
    remote_stop = "remote_stop"


@dataclass
class RobotState:
    timestamp: float
    distance_front: float
    distance_side: float
    distance_hall: float
    angle: float
    total: float = 0
    is_corner: bool = False


@dataclass
class Robot:
    websocket: WebSocket
    mac_address: str = "Undefined"
    status: RobotStatus = RobotStatus.stopped

    def update(self, status: RobotStatus):
        self.status = status
        print(self.status)
