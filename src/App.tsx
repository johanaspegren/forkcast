import { Bot, Check, ChevronRight, CookingPot, FastForward, Minus, Plus, Sparkles, Users } from "lucide-react";
import QRCode from "qrcode";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "./api/rest";
import { connectSessionSocket } from "./api/websocket";
import { PlayerAvatar } from "./components/PlayerAvatar";
import { VotingPoints } from "./components/VotingPoints";
import type { Meal, Proposal, SchoolMenu, Session } from "./game/gameTypes";

const titleCase = (value: string) => value.slice(0, 1).toUpperCase() + value.slice(1);
const SCHOOL_MENU_URL = "https://menu.matildaplatform.com/meals/week/6752f62a2554115c468f8cb8_forskola-skola";

export default function App() {
  const [meals, setMeals] = useState<Meal[]>([]);
  const [schoolMenu, setSchoolMenu] = useState<SchoolMenu | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [playerId, setPlayerId] = useState(localStorage.getItem("forkcast.playerId") ?? "");
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [mealSuggestionCount, setMealSuggestionCount] = useState(3);
  const [error, setError] = useState("");

  useEffect(() => {
    api.meals().then((value) => setMeals(value as Meal[])).catch((err) => setError(err.message));
    api.schoolMenu(SCHOOL_MENU_URL).then(setSchoolMenu).catch(() => undefined);
    const sessionId = new URLSearchParams(window.location.search).get("session");
    if (sessionId) {
      setJoinCode(sessionId);
    }
  }, []);

  useEffect(() => {
    if (!session?.id) return;
    const socket = connectSessionSocket(session.id, setSession);
    return () => socket.close();
  }, [session?.id]);

  const mealById = useMemo(() => Object.fromEntries(meals.map((meal) => [meal.id, meal])), [meals]);
  const currentPlayer = playerId ? session?.players[playerId] : undefined;
  const currentPlayerState = playerId ? session?.player_state[playerId] : undefined;
  const currentTurnId = session?.turn_order.length
    ? session.turn_order[session.current_turn_index % session.turn_order.length]
    : "";
  const currentTurnPlayer = currentTurnId && session ? session.players[currentTurnId] : undefined;
  const canSimulateCurrentTurn = session?.phase !== "NEGOTIATION" || Boolean(currentTurnPlayer?.simulated);

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
      const created = await api.createSession(mealSuggestionCount);
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
      const created = await api.createSession(mealSuggestionCount);
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
          <label>
            Meal suggestions
            <select
              value={mealSuggestionCount}
              onChange={(event) => setMealSuggestionCount(Number(event.target.value))}
            >
              {[2, 3, 4, 5].map((count) => (
                <option key={count} value={count}>
                  {count} meals per player
                </option>
              ))}
            </select>
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
        <button
          className="simulation-button"
          disabled={!canSimulateCurrentTurn}
          onClick={() => run(() => api.simulateNext(session.id))}
        >
          <FastForward size={16} /> {session.phase === "NEGOTIATION" ? "Simulate Current Turn" : "Simulate Next"}
        </button>
      )}

      {session.phase === "LOBBY" && (
        <Lobby
          session={session}
          onStart={() => run(() => api.start(session.id))}
          onAddSimulatedPlayers={() => run(() => api.addSimulatedPlayers(session.id))}
        />
      )}

      {(session.phase === "MEAL_SELECTION" || session.phase === "SECRET_PLACEMENT") && (
        <MealPlanning
          session={session}
          allMeals={meals}
          schoolMenu={schoolMenu}
          meals={mealById}
          playerId={playerId}
          onSubmit={(placements) =>
            run(async () => {
              let next = session;
              const mealIds = placements.map((placement) => placement.meal_id);
              const hasSimulatedPlayers = Object.values(session.players).some((player) => player.simulated);
              if (session.phase === "MEAL_SELECTION") {
                next = await api.selectMeals(session.id, playerId, mealIds);
                if (next.phase === "MEAL_SELECTION" && hasSimulatedPlayers) {
                  next = await api.simulateNext(session.id);
                }
              }
              if (next.phase === "SECRET_PLACEMENT") {
                next = await api.placeMeals(session.id, playerId, placements);
              }
              return next;
            })
          }
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
          onPlayCard={(payload) => run(() => api.playCard(session.id, { player_id: playerId, ...payload }))}
          onPass={() => run(() => api.passTurn(session.id, playerId))}
          onLock={(day, proposalId) => run(() => api.lockDay(session.id, playerId, day, proposalId))}
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
  const shareUrl = `${window.location.origin}/?session=${session.id}`;

  return (
    <section className="stage">
      <div className="join-code">{session.id}</div>
      <p className="muted">Share this session ID or scan the code from another phone.</p>
      <QrShare value={shareUrl} />
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

function QrShare({ value }: { value: string }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    QRCode.toCanvas(canvasRef.current, value, {
      width: 176,
      margin: 1,
      color: {
        dark: "#111617",
        light: "#fff9ed"
      }
    }).catch(() => undefined);
  }, [value]);

  return (
    <div className="qr-share">
      <canvas ref={canvasRef} aria-label="Session QR code" />
      <p>{value}</p>
    </div>
  );
}

function SchoolLunchStrip({ menu }: { menu: SchoolMenu }) {
  return (
    <div className="school-menu-strip">
      <div className="school-menu-title">
        <strong>School lunch</strong>
        <span>{menu.start_date} - {menu.end_date}</span>
      </div>
      <div className="school-menu-days">
        {menu.days.slice(0, 5).map((day) => {
          const date = new Date(day.date);
          const mainCourse = day.courses.find((course) => course.option_name === "Dagens lunch") ?? day.courses[0];
          const greenCourse = day.courses.find((course) => course.option_name === "Dagens gröna");
          return (
            <div className="school-menu-day" key={day.date}>
              <strong>{date.toLocaleDateString("en-US", { weekday: "short" })}</strong>
              <span>{mainCourse?.name ?? "No lunch listed"}</span>
              {greenCourse && <small>{greenCourse.name}</small>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MealPlanning({
  session,
  allMeals,
  schoolMenu,
  meals,
  playerId,
  onSubmit
}: {
  session: Session;
  allMeals: Meal[];
  schoolMenu: SchoolMenu | null;
  meals: Record<string, Meal>;
  playerId: string;
  onSubmit: (placements: Array<{ meal_id: string; day: string; points: number }>) => void;
}) {
  const player = session.players[playerId];
  const state = session.player_state[playerId];
  const [filter, setFilter] = useState<"favourites" | "asian" | "vego">("favourites");
  const [pickedMealId, setPickedMealId] = useState("");
  const [assigned, setAssigned] = useState<Record<string, string | null>>(() => {
    const initial = Object.fromEntries(session.days.map((day, index) => [day, state.selected_meals[index] ?? null]));
    return initial as Record<string, string | null>;
  });
  const [points, setPoints] = useState<Record<string, number>>(() =>
    Object.fromEntries(session.days.map((day) => [day, 0])) as Record<string, number>
  );

  const assignedMeals = Object.values(assigned).filter(Boolean);
  const spent = Object.values(points).reduce((sum, value) => sum + value, 0);
  const remaining = state.voting_points_remaining - spent;
  const plannedCount = assignedMeals.length;

  const filteredMeals = allMeals.filter((meal) => {
    if (filter === "favourites") return player.favourite_meals.includes(meal.id);
    if (filter === "asian") return meal.tags.includes("japanese") || meal.tags.includes("spiced");
    return meal.protein_type === "vegetarian" || meal.tags.includes("vegetarian");
  });

  function assignMeal(day: string, mealId: string | null) {
    setAssigned((current) => {
      const next = { ...current };
      const dayAlreadyFilled = Boolean(next[day]);
      const assignedCount = Object.values(next).filter(Boolean).length;
      if (mealId && !dayAlreadyFilled && assignedCount >= session.max_selected_meals) {
        return next;
      }
      for (const existingDay of session.days) {
        if (mealId && next[existingDay] === mealId) {
          next[existingDay] = null;
        }
      }
      next[day] = mealId;
      return next;
    });
    setPickedMealId("");
  }

  function moveMeal(fromDay: string, toDay: string) {
    setAssigned((current) => {
      const movingMealId = current[fromDay];
      const replacedMealId = current[toDay];
      return { ...current, [fromDay]: replacedMealId, [toDay]: movingMealId };
    });
  }

  function submit() {
    const placements = session.days
      .map((day) => assigned[day] ? { meal_id: assigned[day]!, day, points: points[day] ?? 0 } : null)
      .filter((placement): placement is { meal_id: string; day: string; points: number } => Boolean(placement));
    onSubmit(placements);
  }

  return (
    <section className="stage planning-stage">
      <div className="planning-header">
        <div>
          <h2>Plan the week</h2>
          <p className="muted">{plannedCount} / {session.max_selected_meals} suggestions set · {remaining} points left</p>
        </div>
      </div>
      {schoolMenu && <SchoolLunchStrip menu={schoolMenu} />}
      <div className="filter-tabs">
        {(["favourites", "asian", "vego"] as const).map((option) => (
          <button key={option} className={filter === option ? "filter-tab active" : "filter-tab"} onClick={() => setFilter(option)}>
            {option === "favourites" ? "Favourites" : option === "asian" ? "Asian" : "Vego"}
          </button>
        ))}
      </div>
      <div className="planning-grid">
        <div className="meal-rail">
          {filteredMeals.map((meal) => {
            const isAssigned = assignedMeals.includes(meal.id);
            return (
              <button
                key={meal.id}
                className={pickedMealId === meal.id ? "rail-meal picked" : isAssigned ? "rail-meal assigned" : "rail-meal"}
                draggable
                onClick={() => setPickedMealId((current) => current === meal.id ? "" : meal.id)}
                onDragStart={(event) => event.dataTransfer.setData("text/plain", `meal:${meal.id}`)}
              >
                <span>{meal.emoji}</span>
                <strong>{meal.name}</strong>
                <small>{meal.tags.join(" · ")}</small>
              </button>
            );
          })}
        </div>
        <div className="weekday-dropzone">
          {session.days.map((day) => {
            const mealId = assigned[day];
            const meal = mealId ? meals[mealId] : null;
            return (
              <div
                key={day}
                className={pickedMealId && (meal || plannedCount < session.max_selected_meals) ? "weekday-slot ready" : "weekday-slot"}
                onClick={() => pickedMealId && assignMeal(day, pickedMealId)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                  event.preventDefault();
                  const data = event.dataTransfer.getData("text/plain");
                  if (data.startsWith("meal:")) assignMeal(day, data.replace("meal:", ""));
                  if (data.startsWith("day:")) moveMeal(data.replace("day:", ""), day);
                }}
              >
                <div className="weekday-slot-head">
                  <strong>{titleCase(day)}</strong>
                  {meal && (
                    <button aria-label={`Clear ${day}`} onClick={(event) => {
                      event.stopPropagation();
                      assignMeal(day, null);
                    }}>
                      <Minus size={14} />
                    </button>
                  )}
                </div>
                {meal ? (
                  <div className="slot-meal" draggable onDragStart={(event) => event.dataTransfer.setData("text/plain", `day:${day}`)}>
                    <span>{meal.emoji}</span>
                    <div>
                      <strong>{meal.name}</strong>
                      <small>{meal.tags.join(" · ")}</small>
                    </div>
                  </div>
                ) : (
                  <p>{plannedCount >= session.max_selected_meals ? "Suggestion limit reached" : "Drop meal here"}</p>
                )}
                <div className="slot-points">
                  <button
                    aria-label={`Spend fewer points on ${day}`}
                    disabled={(points[day] ?? 0) <= 0}
                    onClick={(event) => {
                      event.stopPropagation();
                      setPoints((current) => ({ ...current, [day]: Math.max(0, (current[day] ?? 0) - 1) }));
                    }}
                  >
                    <Minus size={14} />
                  </button>
                  <strong>{points[day] ?? 0}</strong>
                  <button
                    aria-label={`Spend more points on ${day}`}
                    disabled={!meal || remaining <= 0}
                    onClick={(event) => {
                      event.stopPropagation();
                      setPoints((current) => ({ ...current, [day]: (current[day] ?? 0) + 1 }));
                    }}
                  >
                    <Plus size={14} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <button className="primary bottom-action" disabled={plannedCount !== session.max_selected_meals || remaining < 0 || state.placed} onClick={submit}>
        Submit Suggestions <Check size={18} />
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
  onPlayCard,
  onPass,
  onLock,
  onComplete
}: {
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  onVote: (proposalId: string, kind: "support" | "withdraw" | "downvote") => void;
  onPlayCard: (payload: { card: string; proposal_id?: string; day?: string; target_day?: string; meal_id?: string }) => void;
  onPass: () => void;
  onLock: (day: string, proposalId: string) => void;
  onComplete: () => void;
}) {
  const currentTurnId = session.turn_order[session.current_turn_index % Math.max(1, session.turn_order.length)];
  const currentTurnPlayer = currentTurnId ? session.players[currentTurnId] : undefined;
  const isYourTurn = currentTurnId === playerId;

  return (
    <section className="stage">
      {session.phase === "NEGOTIATION" && (
        <div className={isYourTurn ? "turn-panel yours" : "turn-panel"}>
          <div>
            <span>Current Turn</span>
            <strong>{currentTurnPlayer ? `${currentTurnPlayer.avatar} ${currentTurnPlayer.name}` : "Setting order"}</strong>
          </div>
          <button className="primary" disabled={!isYourTurn} onClick={onPass}>
            Pass Turn <ChevronRight size={16} />
          </button>
        </div>
      )}
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
            disabled={!isYourTurn || session.phase !== "NEGOTIATION"}
            onVote={onVote}
            onPlayCard={onPlayCard}
            onLock={onLock}
          />
        ))}
      </div>
      {session.turn_log.length > 0 && (
        <div className="turn-log">
          {session.turn_log.map((entry, index) => (
            <p key={`${entry}-${index}`}>{entry}</p>
          ))}
        </div>
      )}
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
  disabled,
  onVote,
  onPlayCard,
  onLock
}: {
  day: string;
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  disabled: boolean;
  onVote: (proposalId: string, kind: "support" | "withdraw" | "downvote") => void;
  onPlayCard: (payload: { card: string; proposal_id?: string; day?: string; target_day?: string; meal_id?: string }) => void;
  onLock: (day: string, proposalId: string) => void;
}) {
  const proposals = Object.values(session.proposals)
    .filter((proposal) => proposal.day === day)
    .sort((a, b) => b.voting_points - a.voting_points);
  const locked = session.week[day];
  const leaderId = proposals[0]?.id ?? "";

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
            disabled={disabled}
            isLeader={proposal.id === leaderId}
            onVote={onVote}
            onPlayCard={onPlayCard}
            onLock={() => onLock(day, proposal.id)}
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
  disabled,
  isLeader,
  onVote,
  onPlayCard,
  onLock
}: {
  proposal: Proposal;
  meal?: Meal;
  session: Session;
  playerId: string;
  disabled: boolean;
  isLeader: boolean;
  onVote: (proposalId: string, kind: "support" | "withdraw" | "downvote") => void;
  onPlayCard: (payload: { card: string; proposal_id?: string }) => void;
  onLock: () => void;
}) {
  const mySupport = proposal.support_points[playerId] ?? 0;
  const canLock = isLeader && proposal.chef_volunteers.length > 0 && proposal.cleanup_volunteers.length > 0;
  const playerState = session.player_state[playerId];
  const canPlayCard = !disabled;
  const cookCommitted = proposal.chef_volunteers.includes(playerId);
  const cleanCommitted = proposal.cleanup_volunteers.includes(playerId);

  return (
    <div className="proposal-card">
      <div className="proposal-main">
        <span className="meal-emoji">{meal?.emoji}</span>
        <div>
          <strong>{meal?.name}</strong>
          <small>{proposal.owners.map((id) => session.players[id]?.name).join(" + ")} · You: {mySupport}</small>
        </div>
      </div>
      <div className="proposal-actions">
        <button
          disabled={disabled}
          aria-label={mySupport > 0 ? "Withdraw vote" : "Downvote proposal"}
          title={mySupport > 0 ? "Withdraw one of your votes" : "Downvote costs 3 Voting Points"}
          onClick={() => onVote(proposal.id, mySupport > 0 ? "withdraw" : "downvote")}
        >
          <Minus size={16} />
        </button>
        <strong className="proposal-score">{proposal.voting_points}</strong>
        <button disabled={disabled} aria-label="Support proposal" onClick={() => onVote(proposal.id, "support")}>
          <Plus size={16} />
        </button>
      </div>
      <div className="chore-actions">
        <button
          className={cookCommitted ? "chore-button active" : "chore-button"}
          disabled={!canPlayCard}
          aria-pressed={cookCommitted}
          onClick={() => onPlayCard({ card: "ILL_COOK", proposal_id: proposal.id })}
        >
          {cookCommitted ? "Un-cook" : "Cook"}
        </button>
        <button
          className={cleanCommitted ? "chore-button active" : "chore-button"}
          disabled={!canPlayCard}
          aria-pressed={cleanCommitted}
          onClick={() => onPlayCard({ card: "ILL_CLEAN", proposal_id: proposal.id })}
        >
          {cleanCommitted ? "Un-clean" : "Clean"}
        </button>
      </div>
      {(proposal.chef_volunteers.length > 0 || proposal.cleanup_volunteers.length > 0) && (
        <div className="volunteer-line">
          {proposal.chef_volunteers.length > 0 && <span>Chef: {proposal.chef_volunteers.map((id) => session.players[id]?.name).join(", ")}</span>}
          {proposal.cleanup_volunteers.length > 0 && <span>Cleanup: {proposal.cleanup_volunteers.map((id) => session.players[id]?.name).join(", ")}</span>}
        </div>
      )}
      <div className="lock-row">
        <button className="lock-button" disabled={disabled || !canLock} onClick={onLock}>
          {canLock ? "Lock" : isLeader ? "Needs chores" : "Not leading"}
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
