import { Bot, Check, ChevronRight, CookingPot, FastForward, Minus, Plus, Sparkles, Users } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { api } from "./api/rest";
import { connectSessionSocket } from "./api/websocket";
import { PlayerAvatar } from "./components/PlayerAvatar";
import { VotingPoints } from "./components/VotingPoints";
import type { Meal, Proposal, Session } from "./game/gameTypes";

const titleCase = (value: string) => value.slice(0, 1).toUpperCase() + value.slice(1);

export default function App() {
  const [meals, setMeals] = useState<Meal[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [playerId, setPlayerId] = useState(localStorage.getItem("forkcast.playerId") ?? "");
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.meals().then((value) => setMeals(value as Meal[])).catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!session?.id) return;
    const socket = connectSessionSocket(session.id, setSession);
    return () => socket.close();
  }, [session?.id]);

  const mealById = useMemo(() => Object.fromEntries(meals.map((meal) => [meal.id, meal])), [meals]);
  const currentPlayer = playerId ? session?.players[playerId] : undefined;
  const currentPlayerState = playerId ? session?.player_state[playerId] : undefined;

  async function run(action: () => Promise<Session>) {
    setError("");
    try {
      setSession(await action());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  async function createAndJoin() {
    setError("");
    try {
      const created = await api.createSession();
      const joined = await api.join(created.id, name || "Johan");
      const id = Object.keys(joined.players).at(-1) ?? "";
      localStorage.setItem("forkcast.playerId", id);
      setPlayerId(id);
      setSession(joined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create session");
    }
  }

  async function createSimulation() {
    setError("");
    try {
      const created = await api.createSession();
      const joined = await api.join(created.id, name || "Johan");
      const id = Object.keys(joined.players).at(-1) ?? "";
      localStorage.setItem("forkcast.playerId", id);
      setPlayerId(id);
      setSession(await api.addSimulatedPlayers(joined.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create simulation");
    }
  }

  async function joinExisting() {
    if (!joinCode.trim()) return;
    const code = joinCode.trim();
    await run(async () => {
      const existing = await api.getSession(code);
      const joined = await api.join(existing.id, name || `Player ${Object.keys(existing.players).length + 1}`);
      const id = Object.keys(joined.players).at(-1) ?? "";
      localStorage.setItem("forkcast.playerId", id);
      setPlayerId(id);
      return joined;
    });
  }

  if (!session || !currentPlayer || !currentPlayerState) {
    return (
      <main className="shell join-screen">
        <section className="brand-panel">
          <div className="brand-mark">
            <CookingPot size={30} />
          </div>
          <p className="eyebrow">Weekly Dinner Draft</p>
          <h1>Forkcast</h1>
          <p className="intro">Create a Sunday planning game, join from phones, and leave with dinner handled.</p>
        </section>

        <section className="panel">
          <label>
            Your name
            <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Johan" />
          </label>
          <button className="primary" onClick={createAndJoin}>
            <Plus size={18} /> Create Session
          </button>
          <button onClick={createSimulation}>
            <Bot size={18} /> Create Simulation
          </button>
        </section>

        <section className="panel">
          <label>
            Session ID
            <input value={joinCode} onChange={(event) => setJoinCode(event.target.value)} placeholder="8 character id" />
          </label>
          <button onClick={joinExisting}>
            <Users size={18} /> Join Session
          </button>
        </section>

        {error && <p className="error">{error}</p>}
      </main>
    );
  }

  const proposals = Object.values(session.proposals);

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">{session.join_code}</p>
          <h1>Forkcast</h1>
        </div>
        <VotingPoints state={currentPlayerState} />
      </header>

      <div className="phase-track">
        <span>{session.phase.replace("_", " ")}</span>
        <strong>{Object.keys(session.players).length} / {session.max_players}</strong>
      </div>

      {error && <p className="error">{error}</p>}

      {session.players[playerId] && Object.values(session.players).some((player) => player.simulated) && (
        <button className="simulation-button" onClick={() => run(() => api.simulateNext(session.id))}>
          <FastForward size={16} /> Simulate Next
        </button>
      )}

      {session.phase === "LOBBY" && (
        <Lobby
          session={session}
          onStart={() => run(() => api.start(session.id))}
          onAddSimulatedPlayers={() => run(() => api.addSimulatedPlayers(session.id))}
        />
      )}

      {session.phase === "MEAL_SELECTION" && (
        <MealSelection
          meals={meals}
          selected={currentPlayerState.selected_meals}
          allowed={currentPlayerState.meal_cards}
          max={session.max_selected_meals}
          onSubmit={(mealIds) => run(() => api.selectMeals(session.id, playerId, mealIds))}
        />
      )}

      {session.phase === "SECRET_PLACEMENT" && (
        <Placement
          session={session}
          meals={mealById}
          playerId={playerId}
          onSubmit={(placements) => run(() => api.placeMeals(session.id, playerId, placements))}
        />
      )}

      {session.phase === "REVEAL" && (
        <Reveal
          proposals={proposals}
          session={session}
          meals={mealById}
          onContinue={() => run(() => api.continueReveal(session.id))}
        />
      )}

      {(session.phase === "NEGOTIATION" || session.phase === "FINAL_VOTE") && (
        <Board
          session={session}
          meals={mealById}
          playerId={playerId}
          onVote={(proposalId, kind) => run(() => api.vote(session.id, playerId, proposalId, kind))}
          onLock={(day, proposalId, chef, cleanup) => run(() => api.lockDay(session.id, day, proposalId, chef, cleanup))}
          onComplete={() => run(() => api.complete(session.id))}
        />
      )}

      {session.phase === "COMPLETE" && <FinalForkcast session={session} meals={mealById} />}
    </main>
  );
}

function Lobby({
  session,
  onStart,
  onAddSimulatedPlayers
}: {
  session: Session;
  onStart: () => void;
  onAddSimulatedPlayers: () => void;
}) {
  const hasRoom = Object.keys(session.players).length < session.max_players;
  const hasSimulatedPlayers = Object.values(session.players).some((player) => player.simulated);

  return (
    <section className="stage">
      <div className="join-code">{session.id}</div>
      <p className="muted">Share this session ID with the other phones.</p>
      <div className="players-grid">
        {Object.values(session.players).map((player) => (
          <PlayerAvatar key={player.id} player={player} />
        ))}
      </div>
      {hasRoom && !hasSimulatedPlayers && (
        <button onClick={onAddSimulatedPlayers}>
          <Bot size={18} /> Add 3 Sim Players
        </button>
      )}
      <button className="primary bottom-action" onClick={onStart}>
        Start Meal Draft <ChevronRight size={18} />
      </button>
    </section>
  );
}

function MealSelection({
  meals,
  allowed,
  selected,
  max,
  onSubmit
}: {
  meals: Meal[];
  allowed: string[];
  selected: string[];
  max: number;
  onSubmit: (mealIds: string[]) => void;
}) {
  const [choice, setChoice] = useState<string[]>(selected);
  const options = meals.filter((meal) => allowed.includes(meal.id));

  function toggle(mealId: string) {
    setChoice((current) => {
      if (current.includes(mealId)) return current.filter((id) => id !== mealId);
      if (current.length >= max) return current;
      return [...current, mealId];
    });
  }

  return (
    <section className="stage">
      <h2>Choose {max} meal cards</h2>
      <div className="meal-grid">
        {options.map((meal) => (
          <button
            key={meal.id}
            className={choice.includes(meal.id) ? "meal-card selected" : "meal-card"}
            onClick={() => toggle(meal.id)}
          >
            <span className="meal-emoji">{meal.emoji}</span>
            <strong>{meal.name}</strong>
            <small>{meal.tags.join(" · ")}</small>
          </button>
        ))}
      </div>
      <button className="primary bottom-action" disabled={choice.length !== max} onClick={() => onSubmit(choice)}>
        Lock Selection <Check size={18} />
      </button>
    </section>
  );
}

function Placement({
  session,
  meals,
  playerId,
  onSubmit
}: {
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  onSubmit: (placements: Array<{ meal_id: string; day: string; points: number }>) => void;
}) {
  const state = session.player_state[playerId];
  const [placements, setPlacements] = useState(
    state.selected_meals.map((mealId, index) => ({
      meal_id: mealId,
      day: session.days[index % session.days.length],
      points: 0
    }))
  );

  const spent = placements.reduce((sum, item) => sum + item.points, 0);

  return (
    <section className="stage">
      <h2>Place meals secretly</h2>
      <p className="muted">{state.voting_points_remaining - spent} points left for placement.</p>
      <div className="placement-list">
        {placements.map((item, index) => (
          <div className="placement-row" key={item.meal_id}>
            <div>
              <span className="meal-emoji small">{meals[item.meal_id]?.emoji}</span>
              <strong>{meals[item.meal_id]?.name}</strong>
            </div>
            <select
              value={item.day}
              onChange={(event) =>
                setPlacements((current) =>
                  current.map((placement, placementIndex) =>
                    placementIndex === index ? { ...placement, day: event.target.value } : placement
                  )
                )
              }
            >
              {session.days.map((day) => (
                <option key={day} value={day}>
                  {titleCase(day)}
                </option>
              ))}
            </select>
            <div className="stepper">
              <button
                aria-label="Spend fewer points"
                onClick={() =>
                  setPlacements((current) =>
                    current.map((placement, placementIndex) =>
                      placementIndex === index ? { ...placement, points: Math.max(0, placement.points - 1) } : placement
                    )
                  )
                }
              >
                <Minus size={16} />
              </button>
              <strong>{item.points}</strong>
              <button
                aria-label="Spend more points"
                disabled={spent >= state.voting_points_remaining}
                onClick={() =>
                  setPlacements((current) =>
                    current.map((placement, placementIndex) =>
                      placementIndex === index ? { ...placement, points: placement.points + 1 } : placement
                    )
                  )
                }
              >
                <Plus size={16} />
              </button>
            </div>
          </div>
        ))}
      </div>
      <button className="primary bottom-action" disabled={state.placed} onClick={() => onSubmit(placements)}>
        Submit Secret Placement <Check size={18} />
      </button>
    </section>
  );
}

function Reveal({
  proposals,
  session,
  meals,
  onContinue
}: {
  proposals: Proposal[];
  session: Session;
  meals: Record<string, Meal>;
  onContinue: () => void;
}) {
  return (
    <section className="stage reveal">
      <Sparkles size={38} />
      <h2>The Forkcast Opens</h2>
      <div className="day-stack">
        {session.days.map((day) => (
          <DayProposals key={day} day={day} proposals={proposals.filter((proposal) => proposal.day === day)} meals={meals} session={session} />
        ))}
      </div>
      <button className="primary bottom-action" onClick={onContinue}>
        Negotiate <ChevronRight size={18} />
      </button>
    </section>
  );
}

function Board({
  session,
  meals,
  playerId,
  onVote,
  onLock,
  onComplete
}: {
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  onVote: (proposalId: string, kind: "support" | "downvote") => void;
  onLock: (day: string, proposalId: string, chef: string[], cleanup: string[]) => void;
  onComplete: () => void;
}) {
  return (
    <section className="stage">
      <div className="rules-strip">
        {session.rules.map((rule) => (
          <div key={rule.id} className={rule.satisfied ? "rule ok" : "rule warn"}>
            <strong>{rule.satisfied ? "OK" : "Rule"}</strong>
            <span>{rule.label}</span>
          </div>
        ))}
      </div>
      <div className="day-stack">
        {session.days.map((day) => (
          <DayColumn
            key={day}
            day={day}
            session={session}
            meals={meals}
            playerId={playerId}
            onVote={onVote}
            onLock={onLock}
          />
        ))}
      </div>
      {session.phase === "FINAL_VOTE" && (
        <button className="primary bottom-action" onClick={onComplete}>
          Final Forkcast <Check size={18} />
        </button>
      )}
    </section>
  );
}

function DayColumn({
  day,
  session,
  meals,
  playerId,
  onVote,
  onLock
}: {
  day: string;
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  onVote: (proposalId: string, kind: "support" | "downvote") => void;
  onLock: (day: string, proposalId: string, chef: string[], cleanup: string[]) => void;
}) {
  const proposals = Object.values(session.proposals)
    .filter((proposal) => proposal.day === day)
    .sort((a, b) => b.voting_points - a.voting_points);
  const locked = session.week[day];

  return (
    <article className={locked ? "day locked" : "day"}>
      <header>
        <h3>{titleCase(day)}</h3>
        {locked && <span className="locked-label">Locked</span>}
      </header>
      {locked ? (
        <div className="locked-meal">
          <span className="meal-emoji">{meals[locked.meal_id]?.emoji}</span>
          <strong>{meals[locked.meal_id]?.name}</strong>
          <small>Chef: {locked.chef.map((id) => session.players[id]?.name).join(", ") || "Unassigned"}</small>
          <small>Cleanup: {locked.cleanup.map((id) => session.players[id]?.name).join(", ") || "Unassigned"}</small>
        </div>
      ) : (
        proposals.map((proposal) => (
          <ProposalCard
            key={proposal.id}
            proposal={proposal}
            meal={meals[proposal.meal_id]}
            session={session}
            playerId={playerId}
            onVote={onVote}
            onLock={(chef, cleanup) => onLock(day, proposal.id, chef, cleanup)}
          />
        ))
      )}
    </article>
  );
}

function DayProposals({
  day,
  proposals,
  meals,
  session
}: {
  day: string;
  proposals: Proposal[];
  meals: Record<string, Meal>;
  session: Session;
}) {
  return (
    <article className="day">
      <h3>{titleCase(day)}</h3>
      {proposals.map((proposal) => (
        <div className="revealed-proposal" key={proposal.id}>
          <span>{meals[proposal.meal_id]?.emoji}</span>
          <strong>{meals[proposal.meal_id]?.name}</strong>
          <small>{proposal.owners.map((id) => session.players[id]?.name).join(" + ")}</small>
          <b>{proposal.voting_points}</b>
        </div>
      ))}
    </article>
  );
}

function ProposalCard({
  proposal,
  meal,
  session,
  playerId,
  onVote,
  onLock
}: {
  proposal: Proposal;
  meal?: Meal;
  session: Session;
  playerId: string;
  onVote: (proposalId: string, kind: "support" | "downvote") => void;
  onLock: (chef: string[], cleanup: string[]) => void;
}) {
  const [chef, setChef] = useState("");
  const [cleanup, setCleanup] = useState("");

  return (
    <div className="proposal-card">
      <div className="proposal-main">
        <span className="meal-emoji">{meal?.emoji}</span>
        <div>
          <strong>{meal?.name}</strong>
          <small>{proposal.owners.map((id) => session.players[id]?.name).join(" + ")}</small>
        </div>
        <b>{proposal.voting_points}</b>
      </div>
      <div className="proposal-actions">
        <button aria-label="Support proposal" onClick={() => onVote(proposal.id, "support")}>
          <Plus size={16} /> Support
        </button>
        <button aria-label="Downvote proposal" onClick={() => onVote(proposal.id, "downvote")}>
          <Minus size={16} /> Downvote
        </button>
      </div>
      <div className="lock-row">
        <select value={chef} onChange={(event) => setChef(event.target.value)}>
          <option value="">Chef</option>
          {Object.values(session.players).map((player) => (
            <option key={player.id} value={player.id}>
              {player.name}
            </option>
          ))}
        </select>
        <select value={cleanup} onChange={(event) => setCleanup(event.target.value)}>
          <option value="">Cleanup</option>
          {Object.values(session.players).map((player) => (
            <option key={player.id} value={player.id}>
              {player.name}
            </option>
          ))}
        </select>
        <button className="lock-button" disabled={!chef} onClick={() => onLock([chef], cleanup ? [cleanup] : [])}>
          Lock
        </button>
      </div>
    </div>
  );
}

function FinalForkcast({ session, meals }: { session: Session; meals: Record<string, Meal> }) {
  return (
    <section className="stage final">
      <p className="eyebrow">The Forkcast Is In</p>
      <h2>Dinner is decided</h2>
      <div className="day-stack">
        {session.days.map((day) => {
          const entry = session.week[day];
          if (!entry) return null;
          return (
            <article className="day locked" key={day}>
              <h3>{titleCase(day)}</h3>
              <div className="locked-meal">
                <span className="meal-emoji">{meals[entry.meal_id]?.emoji}</span>
                <strong>{meals[entry.meal_id]?.name}</strong>
                <small>Chef: {entry.chef.map((id) => session.players[id]?.name).join(", ") || "Unassigned"}</small>
                <small>Cleanup: {entry.cleanup.map((id) => session.players[id]?.name).join(", ") || "Unassigned"}</small>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
