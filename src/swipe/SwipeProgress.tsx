import QRCode from "qrcode";
import { useEffect, useRef, useState } from "react";

import { swipeApi } from "../api/swipe";
import type { RoundView } from "./swipeTypes";

/**
 * The hallway nudge.
 *
 * Async swiping has no lobby and no notifications, so nothing reminds the
 * family that a week is waiting on them. The tablet in the hall is that
 * reminder: who has swiped, who has not, and a code to scan.
 */
export function SwipeProgress({ year, week, weekId }: { year: number; week: number; weekId: string }) {
  const [view, setView] = useState<RoundView | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const swipeUrl = `${window.location.origin}/swipe?from=qr&year=${year}&week=${week}`;

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      swipeApi
        .getRound(weekId, year, week)
        .then((next) => !cancelled && setView(next))
        .catch(() => undefined);
    load();
    const timer = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [weekId, year, week]);

  useEffect(() => {
    // `view` is a dependency because the canvas only enters the DOM once the
    // round has loaded; without it the QR would silently stay blank.
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, swipeUrl, {
      width: 132,
      margin: 1,
      color: { dark: "#24302f", light: "#fff9ed" }
    }).catch(() => undefined);
  }, [swipeUrl, view]);

  if (!view || view.members.length === 0) return null;

  const swiped = view.members.filter((member) => member.swiped_this_round).length;
  const locked = view.round.status === "locked";

  return (
    <section className="swipe-progress">
      <div className="swipe-progress-body">
        <p className="display-kicker">Veckans svep</p>
        <h2>
          {locked
            ? "Veckan är klar"
            : `${swiped} av ${view.members.length} har swipat`}
        </h2>
        <ul className="swipe-progress-members">
          {view.members.map((member) => (
            <li className={member.swiped_this_round ? "done" : "waiting"} key={member.member_id}>
              <span aria-hidden="true">{member.avatar}</span>
              <strong>{member.name}</strong>
              <em>{member.swiped_this_round ? "✓" : "…"}</em>
            </li>
          ))}
        </ul>
        {!locked && <p className="display-note">Skanna för att svepa veckans rätter</p>}
      </div>
      <canvas aria-label="QR-kod till receptsvepet" ref={canvasRef} />
    </section>
  );
}
