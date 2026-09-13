import { Heart, Sparkles, X } from "lucide-react";

import type { DeckCard, Verdict } from "./swipeTypes";

const GROUPS: { verdict: Verdict; label: string; hint: string }[] = [
  { verdict: "superlike", label: "Favoriter", hint: "du lagar gärna" },
  { verdict: "like", label: "Gillar", hint: "gärna i veckan" },
  { verdict: "dislike", label: "Nej tack", hint: "helst inte" }
];

/**
 * What you just voted, and a way to fix it.
 *
 * A mis-swipe is easy and otherwise invisible until it shows up as dinner, so
 * every row can be re-voted here. Verdicts are idempotent, so changing one is
 * just another swipe.
 */
export function VoteSummary({
  cards,
  justSwiped,
  busy,
  onChange
}: {
  cards: DeckCard[];
  justSwiped: Set<string>;
  busy: boolean;
  onChange: (mealId: string, verdict: Verdict) => void;
}) {
  if (cards.length === 0) return null;

  const counts = {
    superlike: cards.filter((c) => c.previous_verdict === "superlike").length,
    like: cards.filter((c) => c.previous_verdict === "like").length,
    dislike: cards.filter((c) => c.previous_verdict === "dislike").length
  };

  return (
    <section className="panel vote-summary">
      <h3>Dina svep</h3>
      <p className="muted">
        {counts.superlike} favoriter · {counts.like} gillar · {counts.dislike} nej tack
      </p>

      {GROUPS.map((group) => {
        const rows = cards.filter((card) => card.previous_verdict === group.verdict);
        if (rows.length === 0) return null;
        return (
          <div className="vote-group" key={group.verdict}>
            <h4>
              {group.label} <span>{group.hint}</span>
            </h4>
            <ul>
              {rows.map((card) => (
                <li key={card.meal_id}>
                  <span className="vote-thumb">
                    {card.thumb_url ? <img alt="" src={card.thumb_url} /> : card.emoji}
                  </span>
                  <span className="vote-name">
                    {card.name}
                    {justSwiped.has(card.meal_id) && <em>nyss</em>}
                  </span>
                  <span className="vote-change">
                    <button
                      aria-label={`Nej tack till ${card.name}`}
                      className={card.previous_verdict === "dislike" ? "active no" : ""}
                      disabled={busy}
                      onClick={() => onChange(card.meal_id, "dislike")}
                      type="button"
                    >
                      <X size={15} />
                    </button>
                    <button
                      aria-label={`Gillar ${card.name}`}
                      className={card.previous_verdict === "like" ? "active yes" : ""}
                      disabled={busy}
                      onClick={() => onChange(card.meal_id, "like")}
                      type="button"
                    >
                      <Heart size={15} />
                    </button>
                    <button
                      aria-label={`${card.name} är en favorit`}
                      className={card.previous_verdict === "superlike" ? "active super" : ""}
                      disabled={busy}
                      onClick={() => onChange(card.meal_id, "superlike")}
                      type="button"
                    >
                      <Sparkles size={14} />
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        );
      })}
    </section>
  );
}
