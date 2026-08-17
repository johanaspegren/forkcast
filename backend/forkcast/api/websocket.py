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

    async def broadcast_heart(self, session: Session, proposal_id: str, player_id: str, event_id: str) -> None:
        proposal = session.proposals[proposal_id]
        day_proposals = [candidate for candidate in session.proposals.values() if candidate.day == proposal.day]
        leader_id = max(
            day_proposals,
            key=lambda candidate: candidate.voting_points * 1000 + len(candidate.supporters),
        ).id
        stale: list[WebSocket] = []
        for websocket in self.connections[session.id]:
            try:
                await websocket.send_json({
                    "event": "HEART",
                    "heart": {
                        "event_id": event_id,
                        "proposal_id": proposal_id,
                        "player_id": player_id,
                        "total": session.realtime_stats.hearts_by_proposal.get(proposal_id, 0),
                        "day": proposal.day,
                        "leader_id": leader_id,
                    },
                })
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session.id, websocket)

    async def broadcast_deleted(self, session_id: str) -> None:
        stale: list[WebSocket] = []
        for websocket in self.connections[session_id]:
            try:
                await websocket.send_json({"event": "SESSION_DELETED", "session_id": session_id})
            except RuntimeError:
                stale.append(websocket)
        for websocket in stale:
            self.disconnect(session_id, websocket)
        self.connections.pop(session_id, None)


manager = ConnectionManager()
