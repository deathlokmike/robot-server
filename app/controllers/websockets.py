from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from app.services.connection_manager import connection_manager
from app.services.types import CleanerStatus, ConnectionType

router = APIRouter(prefix="/ws")


@router.websocket("/client")
async def websocket_image_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket, ConnectionType.client)
    try:
        while True:
            data = await websocket.receive_text()
            status = CleanerStatus(data)
            await connection_manager.send_message_to_cleaner(status)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)


@router.websocket("/cleaner")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket, ConnectionType.cleaner)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Message from cleaner {data}")
            await connection_manager.parse_cleaner_message(websocket, data)
    except WebSocketDisconnect:
        await connection_manager.disconnect_cleaner(websocket)
