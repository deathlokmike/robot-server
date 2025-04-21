import re
from typing import Optional

from fastapi import WebSocket

from app.services.database import CleanerDatabase
from app.services.types import Cleaner, CleanerState, CleanerStatus, ConnectionType


def parse_cleaner_state(data: str) -> CleanerState:
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

    return CleanerState(
        timestamp=float(match.group("t")),
        distance_front=float(match.group("df")),
        distance_side=float(match.group("ds")),
        distance_hall=float(match.group("dh")),
        angle=float(match.group("ang")),
    )


def _find_cleaner_index_by_websocket(
    cleaners: list["Cleaner"], websocket: WebSocket
) -> Optional[int]:
    for i, cleaner in enumerate(cleaners):
        if cleaner.websocket == websocket:
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
        self._db = CleanerDatabase()
        self._cleaners: list[Cleaner] = []
        self._clients: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, type_: ConnectionType):
        await websocket.accept()
        if type_ == ConnectionType.cleaner:
            cleaner = Cleaner(websocket=websocket)
            self._cleaners.append(cleaner)
        elif type_ == ConnectionType.client:
            self._clients.append(websocket)

    async def send_message_to_cleaner(self, status: CleanerStatus):
        for cleaner in self._cleaners:
            if cleaner.status == status:
                continue
            match status:
                case (
                    CleanerStatus.launched,
                    CleanerStatus.checked_camera,
                    CleanerStatus.checked_system,
                ):
                    if cleaner.status != CleanerStatus.stopped:
                        return
                case CleanerStatus.resumed:
                    if cleaner.status == CleanerStatus.launched:
                        return
            try:
                await cleaner.websocket.send_text(status.value)
            except RuntimeError:
                self._cleaners.remove(cleaner)
            if status == CleanerStatus.resumed:
                cleaner.status = CleanerStatus.launched
            else:
                cleaner.status = status

    async def send_data_to_client(self, data: str):
        for client in self._clients:
            await client.send_text(data)

    async def disconnect_cleaner(self, websocket: WebSocket):
        cleaner_index = _find_cleaner_index_by_websocket(self._cleaners, websocket)
        if cleaner_index:
            self._cleaners.pop(cleaner_index)
        await self.send_data_to_client(
            "data:log:vol:-,cur:-,df:-,ds:-,ang:-,ts:-,dh:-,bat:-"
        )

    def disconnect(self, websocket: WebSocket):
        self._clients.remove(websocket)

    async def parse_cleaner_message(self, websocket: WebSocket, data: str):
        cleaner_index = _find_cleaner_index_by_websocket(self._cleaners, websocket)
        if cleaner_index is not None:
            mac_start_index = data.find("mac:")
            log_start_index = data.find("vol:")
            if mac_start_index != -1:
                self._cleaners[cleaner_index].mac_address = data[mac_start_index + 4 :]

            if log_start_index != -1:
                battery_percent = _get_battery_percent(data)
                state = parse_cleaner_state(data)
                self._db.add(self._cleaners[cleaner_index].mac_address, state)
                await self.send_data_to_client(f"data:log:{data},bat:{battery_percent}")

            if data.find("done") != -1:
                self._cleaners[cleaner_index].update(CleanerStatus.stopped)


connection_manager = ConnectionManager()
