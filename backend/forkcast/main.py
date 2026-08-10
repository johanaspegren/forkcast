from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.forkcast.api.sessions import router
from backend.forkcast.api.websocket import manager
from backend.forkcast.game.engine import engine

app = FastAPI(title="Forkcast", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

DIST_DIR = Path(__file__).resolve().parents[2] / "dist"


@app.websocket("/ws/sessions/{session_id}")
async def session_socket(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(session_id, websocket)
    try:
        session = engine.get_session(session_id)
        await websocket.send_json({"event": "SESSION_UPDATED", "session": session.model_dump(mode="json")})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)


if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str) -> FileResponse:
        requested = DIST_DIR / path
        if path and requested.exists() and requested.is_file():
            return FileResponse(requested)
        return FileResponse(DIST_DIR / "index.html")
