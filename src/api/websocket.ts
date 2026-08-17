import type { Session } from "../game/gameTypes";
import type { RealtimeHeartEvent } from "../realtime/hearts";

export function connectSessionSocket(
  sessionId: string,
  onSession: (session: Session) => void,
  onDeleted?: () => void,
  onHeart?: (heart: RealtimeHeartEvent) => void
): WebSocket {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/sessions/${sessionId}`);
  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.event === "SESSION_UPDATED") {
      onSession(payload.session);
    }
    if (payload.event === "SESSION_DELETED") {
      onDeleted?.();
    }
    if (payload.event === "HEART") {
      onHeart?.({
        eventId: payload.heart.event_id,
        proposalId: payload.heart.proposal_id,
        playerId: payload.heart.player_id,
        total: payload.heart.total,
        day: payload.heart.day,
        leaderId: payload.heart.leader_id
      });
    }
  });
  return socket;
}
