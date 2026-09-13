import { useRef, useState } from "react";

import type { DeckCard, Verdict } from "./swipeTypes";

const COMMIT_DISTANCE = 90;

/**
 * One meal card.
 *
 * The gesture is an enhancement, never the only way through: the three buttons
 * below the deck always work. That keeps the deck usable when a drag misfires,
 * on a desktop, and for anyone using the keyboard.
 *
 * Android lessons from the meal planner (progress.md): take pointer capture,
 * keep the live offset in a ref because React state is stale inside
 * pointermove, and set `touch-action: none` so the browser does not steal the
 * gesture for scrolling.
 */
export function SwipeCard({
  card,
  onCommit,
  stacked
}: {
  card: DeckCard;
  onCommit: (verdict: Verdict) => void;
  stacked?: boolean;
}) {
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const dragging = useRef(false);
  const start = useRef({ x: 0, y: 0 });
  const live = useRef({ x: 0, y: 0 });

  function verdictFor(dx: number, dy: number): Verdict | null {
    if (dy < -COMMIT_DISTANCE && Math.abs(dy) > Math.abs(dx)) return "superlike";
    if (dx > COMMIT_DISTANCE) return "like";
    if (dx < -COMMIT_DISTANCE) return "dislike";
    return null;
  }

  function onPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    if (stacked) return;
    dragging.current = true;
    start.current = { x: event.clientX, y: event.clientY };
    live.current = { x: 0, y: 0 };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragging.current) return;
    live.current = { x: event.clientX - start.current.x, y: event.clientY - start.current.y };
    setOffset(live.current);
  }

  function onPointerUp(event: React.PointerEvent<HTMLDivElement>) {
    if (!dragging.current) return;
    dragging.current = false;
    event.currentTarget.releasePointerCapture?.(event.pointerId);
    const verdict = verdictFor(live.current.x, live.current.y);
    setOffset({ x: 0, y: 0 });
    if (verdict) onCommit(verdict);
  }

  const pending = verdictFor(offset.x, offset.y);
  const rotation = offset.x / 18;

  return (
    <div
      className={`swipe-card${stacked ? " stacked" : ""}${pending ? ` hint-${pending}` : ""}`}
      style={
        stacked
          ? undefined
          : { transform: `translate(${offset.x}px, ${offset.y}px) rotate(${rotation}deg)` }
      }
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    >
      <div className={`swipe-card-art protein-${card.protein ?? "okant"}`}>
        {card.thumb_url ? (
          <img alt="" draggable={false} src={card.thumb_url} />
        ) : (
          <span className="swipe-card-emoji">{card.emoji}</span>
        )}
        {pending && <span className={`swipe-stamp ${pending}`}>{stampLabel(pending)}</span>}
      </div>
      <div className="swipe-card-body">
        <strong>{card.name}</strong>
        <small>
          {[
            card.minutes ? `${card.minutes} min` : null,
            card.protein,
            card.thumb_url ? null : "Standardrätt"
          ]
            .filter(Boolean)
            .join(" · ")}
        </small>
        {card.previous_verdict && <em className="swipe-card-revisit">Du svepte den här förut</em>}
      </div>
    </div>
  );
}

function stampLabel(verdict: Verdict) {
  if (verdict === "like") return "JA";
  if (verdict === "dislike") return "NEJ";
  return "FAVORIT";
}
