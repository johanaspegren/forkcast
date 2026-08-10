from collections import defaultdict

from fastapi import WebSocket

from backend.forkcast.game.models import Session


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        self.connections[session_id].discard(websocket)

    async def broadcast(self, session: Session) -> None:
        stale: list[WebSocket] = []
        payload = session.model_dump(mode="json")
        for websocket in self.connections[session.id]:
            try:
                await websocket.send_json({"event": "SESSION_UPDATED", "session": payload})
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session.id, websocket)


manager = ConnectionManager()

