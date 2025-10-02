import re
from typing import Optional

from fastapi import WebSocket

from app.services.database import RobotDatabase
from app.services.types import Robot, RobotState, RobotStatus, ConnectionType


def parse_robot_state(data: str) -> RobotState:
    pattern = re.compile(
        r"vol:(?P<vol>-?\d+(?:\.\d+)?),"
        r"cur:(?P<cur>-?\d+(?:\.\d+)?),"
        r"df:(?P<df>-?\d+(?:\.\d+)?),"
        r"ds:(?P<ds>-?\d+(?:\.\d+)?),"
        r"ang:(?P<ang>-?\d+(?:\.\d+)?),"
        r"t:(?P<t>-?\d+(?:\.\d+)?),"
        r"dh:(?P<dh>-?\d+(?:\.\d+)?)"
    )
    match = pattern.match(data)

    if not match:
        raise ValueError("Invalid input format")

    return RobotState(
        timestamp=float(match.group("t")),
        distance_front=float(match.group("df")),
        distance_side=float(match.group("ds")),
        distance_hall=float(match.group("dh")),
        angle=float(match.group("ang")),
    )


def _find_robot_index_by_websocket(
    robots: list["Robot"], websocket: WebSocket
) -> Optional[int]:
    for i, robot in enumerate(robots):
        if robot.websocket == websocket:
            return i
    return None


def _get_battery_percent(log_data: str) -> float:
    voltage = float(log_data[4 : log_data.find(",cur")])
    min_voltage = 6.0
    max_voltage = 8.4
    percentage = max(
        0, min(100, int(((voltage - min_voltage) / (max_voltage - min_voltage)) * 100))
    )
    return percentage


class ConnectionManager:
    def __init__(self):
        self._db = RobotDatabase()
        self._robots: list[Robot] = [] self._clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, type_: ConnectionType):
        await websocket.accept()
        if type_ == ConnectionType.robot:
            robot = Robot(websocket=websocket)
            self._robots.append(robot)
        elif type_ == ConnectionType.client:
            self._clients.append(websocket)

    async def send_message_to_robot(self, status: RobotStatus):
        for robot in self._robots:
            if robot.status == status:
                continue
            match status:
                case RobotStatus.resumed:
                    if robot.status == RobotStatus.launched:
                        return
            try:
                await robot.websocket.send_text(status.value)
            except RuntimeError:
                self._robots.remove(robot)
            if status == RobotStatus.resumed:
                robot.status = RobotStatus.launched
            else:
                robot.status = status

    async def send_data_to_client(self, data: str):
        for client in self._clients:
            await client.send_text(data)

    async def disconnect_robot(self, websocket: WebSocket):
        robot_index = _find_robot_index_by_websocket(self._robots, websocket)
        if robot_index:
            self._robots.pop(robot_index)
        await self.send_data_to_client(
            "data:log:vol:-,cur:-,df:-,ds:-,ang:-,ts:-,dh:-,bat:-"
        )

    def disconnect(self, websocket: WebSocket):
        self._clients.remove(websocket)

    async def parse_robot_message(self, websocket: WebSocket, data: str):
        robot_index = _find_robot_index_by_websocket(self._robots, websocket)
        if robot_index is None:
            return
        mac_start_index = data.find("mac:")
        log_start_index = data.find("vol:")
        if mac_start_index != -1:
            self._robots[robot_index].mac_address = data[mac_start_index + 4 :]

        if log_start_index != -1:
            battery_percent = _get_battery_percent(data)
            state = parse_robot_state(data)
            self._db.add(self._robots[robot_index].mac_address, state)
            await self.send_data_to_client(f"data:log:{data},bat:{battery_percent}")

        if data.find("done") != -1:
            self._robots[robot_index].update(RobotStatus.stopped)


connection_manager = ConnectionManager()
