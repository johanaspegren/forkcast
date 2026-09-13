import { Check, RefreshCw, RotateCcw } from "lucide-react";

import type { RoundView } from "./swipeTypes";

const DAY_LABELS: Record<string, string> = {
  monday: "Måndag",
  tuesday: "Tisdag",
  wednesday: "Onsdag",
  thursday: "Torsdag",
  friday: "Fredag"
};

export function ProposalScreen({
  view,
  busy,
  memberId,
  onReroll,
  onRerollAll,
  onVolunteer,
  onConfirm,
  onBack
}: {
  view: RoundView;
  busy: boolean;
  memberId: string | null;
  onReroll: (day: string) => void;
  onRerollAll: () => void;
  onVolunteer: (day: string, role: "chef" | "cleanup") => void;
  onConfirm: () => void;
  onBack: () => void;
}) {
  const proposal = view.round.proposal;
  if (!proposal) return null;

  const names = new Map(view.members.map((member) => [member.member_id, member]));
  const locked = view.round.status === "locked";

  return (
    <section className="panel swipe-proposal">
      <h2>{locked ? "Veckan är låst" : "Förslag till veckan"}</h2>
      {view.note && <p className="swipe-note">{view.note}</p>}
      {view.proposal_stale && !locked && (
        <p className="swipe-note warn">
          Någon har swipat sedan förslaget gjordes. Gör om för att räkna med det.
        </p>
      )}

      <ol className="swipe-week">
        {proposal.picks.map((pick) => (
          <li key={pick.day}>
            <div className="swipe-week-day">
              <span>{DAY_LABELS[pick.day] ?? pick.day}</span>
              {!locked && (
                <button disabled={busy} onClick={() => onReroll(pick.day)} type="button">
                  <RefreshCw size={14} /> Byt
                </button>
              )}
            </div>
            <div className="swipe-week-meal">
              <span aria-hidden="true">{pick.meal_emoji}</span>
              <div>
                <strong>{pick.meal_name}</strong>
                {pick.reason && <small>{pick.reason}</small>}
                <em>
                  {pick.chef.length
                    ? `${pick.chef.map((id) => names.get(id)?.name ?? id).join(", ")} lagar`
                    : "Ingen kock än"}
                  {pick.cleanup.length
                    ? ` · ${pick.cleanup.map((id) => names.get(id)?.name ?? id).join(", ")} diskar`
                    : ""}
                </em>
                {!locked && memberId && (
                  <div className="swipe-chores">
                    <button
                      className={pick.chef.includes(memberId) ? "taken" : ""}
                      disabled={busy}
                      onClick={() => onVolunteer(pick.day, "chef")}
                      type="button"
                    >
                      Jag lagar
                    </button>
                    <button
                      className={pick.cleanup.includes(memberId) ? "taken" : ""}
                      disabled={busy}
                      onClick={() => onVolunteer(pick.day, "cleanup")}
                      type="button"
                    >
                      Jag diskar
                    </button>
                  </div>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>

      <div className="swipe-satisfaction">
        {view.members.map((member) => {
          const score = proposal.satisfaction[member.member_id] ?? 0;
          return (
            <span className={score >= 0 ? "good" : "meh"} key={member.member_id}>
              {member.avatar} {member.name} {score >= 0 ? "😊" : "😐"}
            </span>
          );
        })}
      </div>

      {!locked && (
        <div className="swipe-proposal-actions">
          <button className="primary" disabled={busy} onClick={onConfirm} type="button">
            <Check size={18} /> Lås veckan
          </button>
          <button disabled={busy} onClick={onRerollAll} type="button">
            <RotateCcw size={16} /> Gör om allt
          </button>
        </div>
      )}
      <button className="swipe-link" onClick={onBack} type="button">
        Tillbaka
      </button>
    </section>
  );
}
