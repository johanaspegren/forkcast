import { Heart, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { swipeApi } from "../api/swipe";
import { getDisplayWeek, weekId } from "../game/week";
import { ProposalScreen } from "./ProposalScreen";
import { SwipeCard } from "./SwipeCard";
import { VoteSummary } from "./VoteSummary";
import type { DeckCard, RoundView, Verdict } from "./swipeTypes";

const PROFILE_KEY = "forkcast.playerProfile";
const AVATARS = ["🥘", "🍕", "🌮", "🍜", "🥗", "🍛", "🐟", "🍳"];
const FLUSH_EVERY = 3;

type Profile = { name: string; avatar: string; memberId?: string };

function parseWeekParam(value: string | null) {
  const week = Number(value);
  return Number.isInteger(week) && week >= 1 && week <= 53 ? week : null;
}

function parseYearParam(value: string | null) {
  const year = Number(value);
  return Number.isInteger(year) && year >= 2000 && year <= 2100 ? year : null;
}

function readProfile(): Profile {
  try {
    const stored = JSON.parse(localStorage.getItem(PROFILE_KEY) ?? "{}");
    return { name: stored.name ?? "", avatar: stored.avatar ?? AVATARS[0], memberId: stored.memberId };
  } catch {
    return { name: "", avatar: AVATARS[0] };
  }
}

function writeProfile(profile: Profile) {
  const existing = (() => {
    try {
      return JSON.parse(localStorage.getItem(PROFILE_KEY) ?? "{}");
    } catch {
      return {};
    }
  })();
  localStorage.setItem(PROFILE_KEY, JSON.stringify({ ...existing, ...profile }));
}

export default function SwipeGame() {
  const searchParams = new URLSearchParams(window.location.search);
  const fromQr = searchParams.get("from") === "qr";
  const fallbackWeek = getDisplayWeek();
  const requestedYear = parseYearParam(searchParams.get("year"));
  const requestedWeek = parseWeekParam(searchParams.get("week"));
  const week = requestedYear && requestedWeek ? { ...fallbackWeek, year: requestedYear, week: requestedWeek } : fallbackWeek;
  const weekKey = weekId(week.year, week.week);

  const [profile, setProfile] = useState<Profile>(readProfile);
  const [memberId, setMemberId] = useState<string | null>(readProfile().memberId ?? null);
  const [roster, setRoster] = useState<{ member_id: string; name: string; avatar: string }[]>([]);
  const [deck, setDeck] = useState<DeckCard[]>([]);
  const [index, setIndex] = useState(0);
  const [view, setView] = useState<RoundView | null>(null);
  const [screen, setScreen] = useState<"identify" | "swipe" | "done" | "proposal">("identify");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState<DeckCard[]>([]);
  const [justSwiped, setJustSwiped] = useState<Set<string>>(new Set());
  const [promptSwipeAgain, setPromptSwipeAgain] = useState(false);

  // Swipes are flushed in batches, so a phone that drops off the LAN mid-deck
  // loses at most a couple of cards. The endpoint is idempotent.
  const pending = useRef<Record<string, Verdict>>({});
  const attemptedAutoStart = useRef(false);

  useEffect(() => {
    swipeApi.members().then(setRoster).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!memberId) return;
    swipeApi.getRound(weekKey, week.year, week.week).then(setView).catch(() => undefined);
  }, [memberId, weekKey, week.year, week.week]);

  useEffect(() => {
    if (!fromQr || attemptedAutoStart.current || screen !== "identify") return;
    if (!profile.memberId || !profile.name.trim()) return;
    attemptedAutoStart.current = true;
    void startSwiping(profile.memberId, profile.name.trim(), profile.avatar);
  }, [fromQr, profile.memberId, profile.name, profile.avatar, screen]);

  async function loadSummary(id: string | null = memberId) {
    if (!id) return;
    try {
      setSummary(await swipeApi.summary(id));
    } catch {
      // The recap is a nicety; never block the round on it.
    }
  }

  async function changeVote(mealId: string, verdict: Verdict) {
    if (!memberId) return;
    setBusy(true);
    try {
      setView(await swipeApi.sendVerdicts(memberId, weekKey, week.year, week.week, { [mealId]: verdict }));
      await loadSummary();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte ändra rösten");
    }
    setBusy(false);
  }

  async function flush() {
    const batch = pending.current;
    pending.current = {};
    if (!memberId || Object.keys(batch).length === 0) return;
    try {
      setView(await swipeApi.sendVerdicts(memberId, weekKey, week.year, week.week, batch));
    } catch (err) {
      // Put them back so the next flush retries.
      pending.current = { ...batch, ...pending.current };
      setError(err instanceof Error ? err.message : "Kunde inte spara svepen");
    }
  }

  async function startSwiping(id: string, name: string, avatar: string) {
    setBusy(true);
    setError("");
    setPromptSwipeAgain(false);
    try {
      const member = await swipeApi.register(name, avatar, id || undefined);
      setMemberId(member.member_id);
      writeProfile({ name, avatar, memberId: member.member_id });
      setProfile({ name, avatar, memberId: member.member_id });
      const cards = await swipeApi.deck(member.member_id);
      const round = await swipeApi.getRound(weekKey, week.year, week.week).catch(() => null);
      if (round) setView(round);
      setDeck(cards);
      setIndex(0);
      setJustSwiped(new Set());
      await loadSummary(member.member_id);
      const unlocked = round?.round.status !== "locked";
      const showPrompt = fromQr && cards.length === 0 && unlocked;
      setPromptSwipeAgain(showPrompt);
      setScreen(cards.length ? "swipe" : "done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte starta");
    }
    setBusy(false);
  }

  function commit(verdict: Verdict) {
    const card = deck[index];
    if (!card) return;
    pending.current[card.meal_id] = verdict;
    setJustSwiped((current) => new Set(current).add(card.meal_id));
    const next = index + 1;
    setIndex(next);
    if (Object.keys(pending.current).length >= FLUSH_EVERY || next >= deck.length) void flush();
    if (next >= deck.length) {
      setScreen("done");
      void flush().then(() => loadSummary());
    }
  }

  function swipeAgain() {
    if (summary.length === 0) {
      void startSwiping(memberId ?? "", profile.name, profile.avatar);
      return;
    }
    setPromptSwipeAgain(false);
    setDeck(summary);
    setIndex(0);
    setJustSwiped(new Set());
    setScreen("swipe");
  }

  async function propose() {
    setBusy(true);
    setError("");
    try {
      await flush();
      setView(await swipeApi.propose(weekKey, week.year, week.week));
      setScreen("proposal");
      // Progressive enhancement: the deterministic week is already on screen.
      // If an API key is configured the AI may pick a different near-tied week
      // and write better reasons; if not, this is a no-op and nothing changes.
      void swipeApi
        .enhance(weekKey, week.year, week.week)
        .then((enhanced) => enhanced.round.proposal_ai_used && setView(enhanced))
        .catch(() => undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Kunde inte skapa förslag");
    }
    setBusy(false);
  }

  async function act(action: () => Promise<RoundView>) {
    setBusy(true);
    setError("");
    try {
      setView(await action());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Något gick fel");
    }
    setBusy(false);
  }

  const header = (
    <header className="topbar">
      <div className="swipe-topline">
        <h1>Veckans svep</h1>
        {screen === "swipe" && (
          <p className="swipe-counter">
            {index + 1} / {deck.length}
          </p>
        )}
      </div>
    </header>
  );

  if (screen === "identify") {
    return (
      <main className="shell recipe-shell">
        {header}
        <section className="panel">
          <p className="eyebrow">Vem är du?</p>
          {roster.length > 0 && (
            <div className="swipe-roster">
              {roster.map((member) => (
                <button
                  className="swipe-roster-member"
                  key={member.member_id}
                  onClick={() => startSwiping(member.member_id, member.name, member.avatar)}
                  type="button"
                >
                  <span aria-hidden="true">{member.avatar}</span>
                  <strong>{member.name}</strong>
                </button>
              ))}
            </div>
          )}

          <label>
            Nytt namn
            <input
              onChange={(event) => setProfile({ ...profile, name: event.target.value })}
              placeholder="Amanda"
              value={profile.name}
            />
          </label>
          <div className="avatar-picker" aria-label="Välj avatar">
            {AVATARS.map((avatar) => (
              <button
                aria-pressed={profile.avatar === avatar}
                className={profile.avatar === avatar ? "avatar-choice selected" : "avatar-choice"}
                key={avatar}
                onClick={() => setProfile({ ...profile, avatar })}
                type="button"
              >
                {avatar}
              </button>
            ))}
          </div>
          <button
            className="primary"
            disabled={!profile.name.trim() || busy}
            onClick={() => startSwiping(profile.memberId ?? "", profile.name.trim(), profile.avatar)}
            type="button"
          >
            Börja svepa
          </button>
          {error && <p className="error">{error}</p>}
        </section>
      </main>
    );
  }

  if (screen === "proposal" && view) {
    return (
      <main className="shell recipe-shell">
        {header}
        <ProposalScreen
          busy={busy}
          onBack={() => setScreen("done")}
          onConfirm={() => act(() => swipeApi.confirm(weekKey, week.year, week.week))}
          onReroll={(day) => act(() => swipeApi.reroll(weekKey, week.year, week.week, day))}
          onRerollAll={() => act(() => swipeApi.reroll(weekKey, week.year, week.week))}
          onVolunteer={(day, role) =>
            memberId && act(() => swipeApi.volunteer(weekKey, week.year, week.week, day, memberId, role))
          }
          memberId={memberId}
          view={view}
        />
        {error && <p className="error">{error}</p>}
      </main>
    );
  }

  if (screen === "done") {
    const waiting = view?.members.filter((member) => !member.swiped_this_round) ?? [];
    const locked = view?.round.status === "locked";
    return (
      <main className="shell recipe-shell">
        {header}
        <section className="panel swipe-done">
          <h2>{promptSwipeAgain ? "Swipe again?" : `Klart, ${profile.name}!`}</h2>
          <p className="muted">
            {promptSwipeAgain
              ? "Du har redan svept allt i veckans kortlek. Du kan ändra dina röster här nedan."
              : view
              ? `${view.members.filter((m) => m.swiped_this_round).length} av ${view.members.length} i familjen har swipat den här veckan.`
              : "Dina svep är sparade."}
          </p>
          {waiting.length > 0 && !locked && (
            <p className="swipe-note">Väntar på {waiting.map((member) => member.name).join(", ")}.</p>
          )}
          {locked ? (
            <p className="swipe-note">
              Veckan är redan låst och syns på tavlan. Dina svep sparas till nästa vecka.
            </p>
          ) : (
            <button className="primary" disabled={busy} onClick={propose} type="button">
              <Sparkles size={18} /> Skapa veckans förslag
            </button>
          )}
          {view?.round.proposal && (
            <button onClick={() => setScreen("proposal")} type="button">
              {locked ? "Visa veckan" : "Visa förslaget"}
            </button>
          )}
          <button
            className="swipe-link"
            onClick={() => (promptSwipeAgain ? swipeAgain() : startSwiping(memberId ?? "", profile.name, profile.avatar))}
            type="button"
          >
            {promptSwipeAgain ? "Svep igen" : "Svep fler rätter"}
          </button>
          {error && <p className="error">{error}</p>}
        </section>
        <VoteSummary busy={busy} cards={summary} justSwiped={justSwiped} onChange={changeVote} />
      </main>
    );
  }

  const card = deck[index];
  const upcoming = deck[index + 1];

  return (
    <main className="shell recipe-shell swipe-shell">
      {header}
      <div className="swipe-below-header">
        <div className="swipe-stage">
          {upcoming && <SwipeCard card={upcoming} onCommit={() => undefined} stacked />}
          {card && <SwipeCard card={card} key={card.meal_id} onCommit={commit} />}
        </div>
        <div className="swipe-actions">
          <button aria-label="Nej tack" className="swipe-no" onClick={() => commit("dislike")} type="button">
            <X size={28} />
          </button>
          <button aria-label="Favorit, jag lagar den" className="swipe-super" onClick={() => commit("superlike")} type="button">
            <Sparkles size={24} />
          </button>
          <button aria-label="Gillar" className="swipe-yes" onClick={() => commit("like")} type="button">
            <Heart size={28} />
          </button>
        </div>
        <p className="swipe-hint">Vänster: nej tack · Höger: gillar · Upp: favorit och jag lagar.</p>
      </div>
      {error && <p className="error">{error}</p>}
    </main>
  );
}
