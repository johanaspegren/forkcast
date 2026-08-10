import type { Session } from "../game/gameTypes";

export function connectSessionSocket(sessionId: string, onSession: (session: Session) => void): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/sessions/${sessionId}`);
  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.event === "SESSION_UPDATED") {
      onSession(payload.session);
    }
  });
  return socket;
}

