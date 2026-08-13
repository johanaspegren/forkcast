import { Bot, Check, ChevronLeft, ChevronRight, CookingPot, FastForward, Info, Minus, Plus, Save, Sparkles, Users } from "lucide-react";
import QRCode from "qrcode";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "./api/rest";
import { connectSessionSocket } from "./api/websocket";
import { PlayerAvatar } from "./components/PlayerAvatar";
import { VotingPoints } from "./components/VotingPoints";
import type { Meal, Proposal, SavedWeek, SchoolMenu, Session } from "./game/gameTypes";
import { uiAssets } from "./uiAssets";

const titleCase = (value: string) => value.slice(0, 1).toUpperCase() + value.slice(1);
const SAVED_WEEKS_KEY = "forkcast.savedWeeks";
const SCHOOL_MENU_URL = "https://menu.matildaplatform.com/meals/week/6752f62a2554115c468f8cb8_forskola-skola";
const defaultCrewLabels = { cook: "Cook", clean: "Cleaner" };
const defaultDayStatusLabels = { today: "Today", reserved: "Reserved", leading: "Leading", open: "Open" };
const defaultNutritionLabels = { calories: "cals", protein: "prots" };
const defaultStatusLabels = { mock: "Mock demo", live: "Updates live" };

function getIsoWeek(date = new Date()) {
  const normalized = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = normalized.getUTCDay() || 7;
  normalized.setUTCDate(normalized.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(normalized.getUTCFullYear(), 0, 1));
  const week = Math.ceil(((normalized.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return { year: normalized.getUTCFullYear(), week };
}

function getDefaultWeekOffset(date = new Date()) {
  return date.getDay() === 0 ? 1 : 0;
}

function getDisplayWeek(weekOffset = getDefaultWeekOffset(), date = new Date()) {
  const target = new Date(date);
  target.setDate(target.getDate() + weekOffset * 7);
  const { year, week } = getIsoWeek(target);
  const day = target.getDay() || 7;
  const start = new Date(target);
  start.setDate(target.getDate() - day + 1);
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  return { year, week, start, end };
}

function formatShortDateRange(start: Date, end: Date) {
  const formatter = new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric" });
  return `${formatter.format(start)} - ${formatter.format(end)}`;
}

function weekId(year: number, week: number) {
  return `${year}-W${String(week).padStart(2, "0")}`;
}

function parseWeekParam(value: string | null, fallbackYear: number) {
  if (!value) return null;
  const isoMatch = value.match(/^(\d{4})-?W?(\d{1,2})$/i);
  if (isoMatch) {
    return { year: Number(isoMatch[1]), week: Number(isoMatch[2]) };
  }
  const week = Number(value);
  if (Number.isInteger(week) && week >= 1 && week <= 53) {
    return { year: fallbackYear, week };
  }
  return null;
}

function slugId(value: string) {
  const slug = value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return slug || "unassigned";
}

function savedWeekToSession(savedWeek: SavedWeek): Session {
  const players: Session["players"] = {};
  const ensurePlayer = (name: string) => {
    const id = slugId(name);
    if (!players[id]) {
      players[id] = { id, name, avatar: "🍽️", favourite_meals: [], simulated: false };
    }
    return id;
  };

  const week = Object.fromEntries(
    savedWeek.days.map((day) => {
      const entry = savedWeek.plan[day];
      return [
        day,
        entry
          ? {
              meal_id: entry.meal_id,
              chef: entry.chef.map(ensurePlayer),
              cleanup: entry.cleanup.map(ensurePlayer),
              rule_exceptions: entry.rule_exceptions
            }
          : null
      ];
    })
  );

  return {
    id: savedWeek.id,
    join_code: savedWeek.id,
    phase: "COMPLETE",
    days: savedWeek.days,
    players,
    player_state: {},
    proposals: {},
    week,
    rules: [],
    turn_order: Object.keys(players),
    current_turn_index: 0,
    turn_log: [`Saved Forkcast loaded for Week ${savedWeek.week}.`],
    max_players: Math.max(4, Object.keys(players).length),
    starting_voting_points: 10,
    max_selected_meals: 3,
    max_action_cards_played: 2,
    rule_overrides: savedWeek.rule_overrides,
    general_assembly: {},
    general_assembly_threshold: 4
  };
}

const menuThemes = [
  {
    className: "theme-brasserie",
    active: true,
    label: "Table d'Hôte",
    venue: "Menu de la Semaine",
    tagline: "Cinq soirs, zéro compromis.",
    badgeLabel: "Plat du Jour",
    crewLabels: { cook: "Chef", clean: "Plonge" },
    detailsWord: "détails",
    footerHint: "Touchez un plat pour les ragots de cuisine",
    dayStatusLabels: { today: "Ce soir", reserved: "Réservé", leading: "En tête", open: "Libre" },
    dayNames: {
      monday: "Lundi",
      tuesday: "Mardi",
      wednesday: "Mercredi",
      thursday: "Jeudi",
      friday: "Vendredi",
      saturday: "Samedi",
      sunday: "Dimanche"
    } as Record<string, string> | undefined,
    nutritionLabels: { calories: "cal", protein: "prot." },
    statusLabels: { mock: "Démo", live: "En direct" },
    phaseLabels: {
      LOBBY: "Salon",
      MEAL_SELECTION: "Choix des plats",
      SECRET_PLACEMENT: "Placement secret",
      REVEAL: "Révélation",
      NEGOTIATION: "Négociation",
      RULE_RESOLUTION: "Résolution",
      FINAL_VOTE: "Vote final",
      COMPLETE: "Terminé"
    } as Record<string, string> | undefined
  },
  {
    className: "theme-artdeco",
    active: true,
    label: "The Gatsby Room",
    venue: "Supper Club Menu",
    tagline: "Bootleg jazz, legitimate dinner.",
    badgeLabel: "Tonight's Headliner",
    crewLabels: { cook: "Chef", clean: "Busser" },
    detailsWord: "dossier",
    footerHint: "Tap a dish. The band plays on.",
    dayStatusLabels: { today: "Tonight", reserved: "Booked", leading: "Headlining", open: "Open Table" },
    dayNames: undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  },
  {
    className: "theme-pizzeria",
    active: true,
    label: "Family Owned Since Forever",
    venue: "Forkcast's Famous Kitchen",
    tagline: "Love at first bite.",
    badgeLabel: "Tonight's Special",
    crewLabels: { cook: "Pizzaiolo", clean: "Busboy" },
    detailsWord: "specials",
    footerHint: "Tap a dish. No substitutions, capisce?",
    dayStatusLabels: { today: "Tonight", reserved: "On The Menu", leading: "Crowd Favorite", open: "Ask Your Server" },
    dayNames: undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  },
  {
    className: "theme-neko",
    active: true,
    label: "🐱 Lucky Cat カフェ",
    venue: "Neko カフェ Menu",
    tagline: "Kawaii bites, big feelings!!!",
    badgeLabel: "Today's Fave",
    crewLabels: { cook: "Itamae", clean: "Kouhai" },
    detailsWord: "menu",
    footerHint: "Tap a dish. Purr-fect picks ahead!!!",
    dayStatusLabels: { today: "Tonight!!!", reserved: "On Deck", leading: "Fan Favorite", open: "Ask Nyan~" },
    dayNames: {
      monday: "月曜日",
      tuesday: "火曜日",
      wednesday: "水曜日",
      thursday: "木曜日",
      friday: "金曜日",
      saturday: "土曜日",
      sunday: "日曜日"
    } as Record<string, string> | undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  },
  {
    className: "theme-chalkboard",
    active: false,
    label: "Bistro Chalkboard",
    venue: "Tonight's Board",
    tagline: "Chalked up fresh, wiped clean by Sunday.",
    badgeLabel: "Today's Pick",
    crewLabels: defaultCrewLabels,
    detailsWord: "details",
    footerHint: "Tap a dish for kitchen gossip",
    dayStatusLabels: defaultDayStatusLabels,
    dayNames: undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  },
  {
    className: "theme-gazette",
    active: false,
    label: "Forkcast Gazette",
    venue: "Forkcast Menu",
    tagline: "All the dinner that's fit to print.",
    badgeLabel: "Today's Pick",
    crewLabels: defaultCrewLabels,
    detailsWord: "details",
    footerHint: "Tap a dish for kitchen gossip",
    dayStatusLabels: defaultDayStatusLabels,
    dayNames: undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  },
  {
    className: "theme-diner",
    active: false,
    label: "Diner Ticket",
    venue: "Order Up",
    tagline: "Kitchen's open. No substitutions.",
    badgeLabel: "Today's Pick",
    crewLabels: defaultCrewLabels,
    detailsWord: "details",
    footerHint: "Tap a dish for kitchen gossip",
    dayStatusLabels: defaultDayStatusLabels,
    dayNames: undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  },
  {
    className: "theme-scoreboard",
    active: false,
    label: "Family Scoreboard",
    venue: "Dinner Draft Results",
    tagline: "Voted, plated, and locked in.",
    badgeLabel: "Today's Pick",
    crewLabels: defaultCrewLabels,
    detailsWord: "details",
    footerHint: "Tap a dish for kitchen gossip",
    dayStatusLabels: defaultDayStatusLabels,
    dayNames: undefined,
    nutritionLabels: defaultNutritionLabels,
    statusLabels: defaultStatusLabels,
    phaseLabels: undefined
  }
];
const activeMenuThemes = menuThemes.filter((menuTheme) => menuTheme.active);
const mealDisplayDetails: Record<string, { ingredients: string[]; calories: number; protein: number; bit: string }> = {
  salmon: {
    ingredients: ["salmon", "lemon", "potatoes", "dill", "peas"],
    calories: 620,
    protein: 39,
    bit: "Arrives wearing a tiny lemon cape."
  },
  tacos: {
    ingredients: ["beef mince", "tortillas", "tomato", "corn", "cheese"],
    calories: 710,
    protein: 34,
    bit: "Crunch level: family meeting loud."
  },
  pasta: {
    ingredients: ["pasta", "basil pesto", "parmesan", "tomatoes", "spinach"],
    calories: 640,
    protein: 23,
    bit: "Green, twirly, and suspiciously persuasive."
  },
  chicken_curry: {
    ingredients: ["chicken", "rice", "coconut milk", "curry spices", "carrot"],
    calories: 690,
    protein: 41,
    bit: "Mildly spicy. Dramatically fragrant."
  },
  pizza: {
    ingredients: ["pizza dough", "tomato sauce", "mozzarella", "ham", "olives"],
    calories: 780,
    protein: 31,
    bit: "Technically round. Emotionally Friday."
  },
  yakiniku: {
    ingredients: ["beef", "rice", "soy", "ginger", "sesame"],
    calories: 730,
    protein: 42,
    bit: "Tiny steak vacation, bowl edition."
  },
  tomato_soup: {
    ingredients: ["tomatoes", "onion", "cream", "basil", "bread"],
    calories: 480,
    protein: 16,
    bit: "Soup with main-character confidence."
  },
  burgers: {
    ingredients: ["beef patty", "bun", "lettuce", "cheddar", "pickle"],
    calories: 820,
    protein: 38,
    bit: "Stacked taller than the chore excuses."
  },
  teriyaki_bowl: {
    ingredients: ["chicken", "rice", "teriyaki sauce", "broccoli", "sesame"],
    calories: 660,
    protein: 40,
    bit: "Sticky, shiny, and very pleased with itself."
  },
  veggie_chili: {
    ingredients: ["beans", "tomato", "pepper", "corn", "rice"],
    calories: 560,
    protein: 24,
    bit: "Bean diplomacy in a warm bowl."
  }
};
const MOCK_DISPLAY_MEALS: Meal[] = [
  { id: "salmon", name: "Lemon Salmon", emoji: "🐟", tags: ["fish", "quick"], protein_type: "fish", minced_meat: false, fish: true },
  { id: "tacos", name: "Taco Night", emoji: "🌮", tags: ["minced", "family"], protein_type: "beef", minced_meat: true, fish: false },
  { id: "pasta", name: "Pesto Pasta", emoji: "🍝", tags: ["quick", "vegetarian"], protein_type: "vegetarian", minced_meat: false, fish: false },
  { id: "chicken_curry", name: "Chicken Curry", emoji: "🍛", tags: ["chicken", "spiced"], protein_type: "chicken", minced_meat: false, fish: false },
  { id: "pizza", name: "Friday Pizza", emoji: "🍕", tags: ["weekend", "family"], protein_type: "mixed", minced_meat: false, fish: false }
];
const MOCK_WEEKLY_SESSION: Session = {
  id: "mock-week",
  join_code: "DEMO-WEEK",
  phase: "COMPLETE",
  days: ["monday", "tuesday", "wednesday", "thursday", "friday"],
  players: {
    johan: { id: "johan", name: "Johan", avatar: "🥘", favourite_meals: ["salmon", "tacos", "pasta"], simulated: false },
    anna: { id: "anna", name: "Anna", avatar: "🍕", favourite_meals: ["pizza", "pasta", "chicken_curry"], simulated: false },
    elsa: { id: "elsa", name: "Elsa", avatar: "🌮", favourite_meals: ["tacos", "salmon", "pizza"], simulated: false },
    oscar: { id: "oscar", name: "Oscar", avatar: "🍜", favourite_meals: ["chicken_curry", "pasta", "salmon"], simulated: false }
  },
  player_state: {},
  proposals: {},
  week: {
    monday: { meal_id: "salmon", chef: ["johan"], cleanup: ["anna"], rule_exceptions: [] },
    tuesday: { meal_id: "tacos", chef: ["elsa"], cleanup: ["oscar"], rule_exceptions: [] },
    wednesday: { meal_id: "pasta", chef: ["anna"], cleanup: ["johan"], rule_exceptions: [] },
    thursday: { meal_id: "chicken_curry", chef: ["oscar"], cleanup: ["elsa"], rule_exceptions: [] },
    friday: { meal_id: "pizza", chef: ["johan", "anna"], cleanup: ["elsa", "oscar"], rule_exceptions: [] }
  },
  rules: [
    { id: "fish", label: "One fish dinner", level: "house", satisfied: true, detail: "Lemon Salmon covers fish this week." },
    { id: "minced", label: "Only one minced-meat dinner", level: "house", satisfied: true, detail: "Taco Night is the only minced-meat dinner." }
  ],
  turn_order: ["johan", "anna", "elsa", "oscar"],
  current_turn_index: 0,
  turn_log: ["Mock week loaded for hallway display testing."],
  max_players: 4,
  starting_voting_points: 10,
  max_selected_meals: 3,
  max_action_cards_played: 2,
  rule_overrides: [],
  general_assembly: {},
  general_assembly_threshold: 4
};

export default function App() {
  const searchParams = new URLSearchParams(window.location.search);
  const isDisplayMode = window.location.pathname.startsWith("/display");
  const isMockDisplay = isDisplayMode && (searchParams.get("mock") === "1" || searchParams.get("session") === "mock");
  const sessionId = searchParams.get("session");
  const requestedWeek = parseWeekParam(searchParams.get("week"), getDisplayWeek().year);
  const [meals, setMeals] = useState<Meal[]>(MOCK_DISPLAY_MEALS);
  const [schoolMenu, setSchoolMenu] = useState<SchoolMenu | null>(null);
  const [session, setSession] = useState<Session | null>(() => isMockDisplay ? MOCK_WEEKLY_SESSION : null);
  const [playerId, setPlayerId] = useState(localStorage.getItem("forkcast.playerId") ?? "");
  const [name, setName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [mealSuggestionCount, setMealSuggestionCount] = useState(3);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isMockDisplay) return;
    api.meals().then((value) => setMeals(value as Meal[])).catch((err) => setError(err.message));
    api.schoolMenu(SCHOOL_MENU_URL).then(setSchoolMenu).catch(() => undefined);
    if (sessionId && !isMockDisplay) {
      setJoinCode(sessionId);
      if (isDisplayMode) {
        api.getSession(sessionId).then(setSession).catch((err) => setError(err.message));
      }
    } else if (isDisplayMode) {
      const selectedWeek = requestedWeek ?? getDisplayWeek();
      api.getSavedWeek(weekId(selectedWeek.year, selectedWeek.week))
        .then((savedWeek) => setSession(savedWeekToSession(savedWeek)))
        .catch(() => undefined);
    }
  }, [isDisplayMode, isMockDisplay, requestedWeek?.week, requestedWeek?.year, sessionId]);

  useEffect(() => {
    if (!session?.id || session.id === MOCK_WEEKLY_SESSION.id) return;
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

  if (isDisplayMode) {
    return (
        <DisplayScreen
          session={session}
          meals={mealById}
          joinCode={joinCode}
          error={error}
          onJoinCodeChange={setJoinCode}
          onLoad={() => run(() => api.getSession(joinCode))}
          onLoadMock={() => setSession(MOCK_WEEKLY_SESSION)}
          onSavedWeekLoad={setSession}
          requestedWeek={requestedWeek}
        />
      );
  }

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
          <div className="brand-sparkles" aria-hidden="true">
            <img src={uiAssets.sparkle} alt="" />
            <img src={uiAssets.heart} alt="" />
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
                if (next.phase === "SECRET_PLACEMENT" && hasSimulatedPlayers) {
                  next = await api.simulateNext(session.id);
                }
              }
              if (next.phase === "REVEAL") {
                next = await api.continueReveal(session.id);
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
          onUnlock={(day) => run(() => api.unlockDay(session.id, playerId, day))}
          onGeneralAssembly={(ruleId, points) => run(() => api.generalAssembly(session.id, playerId, ruleId, points))}
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
        dark: "#24302f",
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

function DisplayScreen({
  session,
  meals,
  joinCode,
  error,
  onJoinCodeChange,
  onLoad,
  onLoadMock,
  onSavedWeekLoad,
  requestedWeek
}: {
  session: Session | null;
  meals: Record<string, Meal>;
  joinCode: string;
  error: string;
  onJoinCodeChange: (value: string) => void;
  onLoad: () => void;
  onLoadMock: () => void;
  onSavedWeekLoad: (session: Session | null) => void;
  requestedWeek: { year: number; week: number } | null;
}) {
  const displayParams = new URLSearchParams(window.location.search);
  const isLiveSessionDisplay = Boolean(displayParams.get("session"));
  const isSavedMockDisplay = displayParams.get("mock") === "1" || displayParams.get("session") === "mock";
  const requestedTheme = new URLSearchParams(window.location.search).get("theme");
  const forcedTheme = menuThemes.find(
    (menuTheme) => menuTheme.className === requestedTheme || menuTheme.className === `theme-${requestedTheme}`
  );
  const [activeIndex, setActiveIndex] = useState(0);
  const [selectedDay, setSelectedDay] = useState("");
  const [displayWeekOffset, setDisplayWeekOffset] = useState(() => {
    if (!requestedWeek) return getDefaultWeekOffset();
    const currentWeek = getDisplayWeek(0);
    return requestedWeek.week - currentWeek.week + (requestedWeek.year - currentWeek.year) * 52;
  });
  const [savedWeekError, setSavedWeekError] = useState("");

  const advanceTheme = () => setActiveIndex((current) => (current + 1) % activeMenuThemes.length);

  useEffect(() => {
    if (forcedTheme || activeMenuThemes.length < 2) return undefined;
    const timer = window.setTimeout(advanceTheme, 22000);
    return () => window.clearTimeout(timer);
  }, [forcedTheme, activeIndex]);

  useEffect(() => {
    if (!session) return;
    setSelectedDay((current) => current && session.days.includes(current) ? current : session.days[0] ?? "");
  }, [session]);

  const theme = forcedTheme ?? activeMenuThemes[activeIndex] ?? menuThemes[0];
  const today = new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  const defaultWeekOffset = getDefaultWeekOffset();
  const displayWeek = getDisplayWeek(displayWeekOffset);
  const displayWeekLabel = `Week ${displayWeek.week} · ${displayWeek.year}`;
  const displayWeekRange = formatShortDateRange(displayWeek.start, displayWeek.end);
  const dayLabel = (day: string) => theme.dayNames?.[day] ?? titleCase(day);

  async function loadSavedWeekForOffset(nextOffset: number) {
    setDisplayWeekOffset(nextOffset);
    if (isLiveSessionDisplay || isSavedMockDisplay) return;
    setSavedWeekError("");
    try {
      const selectedWeek = getDisplayWeek(nextOffset);
      const savedWeek = await api.getSavedWeek(weekId(selectedWeek.year, selectedWeek.week));
      onSavedWeekLoad(savedWeekToSession(savedWeek));
    } catch (err) {
      onSavedWeekLoad(null);
      setSavedWeekError(`No saved Forkcast for Week ${getDisplayWeek(nextOffset).week}.`);
    }
  }

  if (!session) {
    return (
      <main className="display-shell display-setup">
        <section className="display-menu">
          <p className="display-kicker">Hallway menu</p>
          <h1>Forkcast</h1>
          <p className="display-note">
            {savedWeekError || `No saved Forkcast found for ${displayWeekLabel}. Load a live session or save this week from a phone.`}
          </p>
          <div className="display-week-nav" aria-label="Displayed week">
            <button type="button" onClick={() => loadSavedWeekForOffset(displayWeekOffset - 1)}>
              <ChevronLeft size={18} /> Previous Week
            </button>
            <div>
              <strong>{displayWeekLabel}</strong>
              <span>{displayWeekRange}</span>
              {defaultWeekOffset > 0 && displayWeekOffset === defaultWeekOffset && <small>Planning week</small>}
            </div>
            <button type="button" onClick={() => loadSavedWeekForOffset(0)} disabled={displayWeekOffset === 0}>
              Current Week
            </button>
            <button type="button" onClick={() => loadSavedWeekForOffset(displayWeekOffset + 1)}>
              Next Week <ChevronRight size={18} />
            </button>
          </div>
          <div className="display-load">
            <input value={joinCode} onChange={(event) => onJoinCodeChange(event.target.value)} placeholder="Session ID" />
            <button className="primary" onClick={onLoad}>Load Menu</button>
          </div>
          <button className="display-mock-button" onClick={onLoadMock}>Try mock week</button>
          {error && <p className="error">{error}</p>}
        </section>
      </main>
    );
  }

  const phaseLabel = theme.phaseLabels?.[session.phase] ?? session.phase.replace("_", " ");

  const menuEntries = session.days.map((day) => {
    const locked = session.week[day];
    const leadingProposal = Object.values(session.proposals)
      .filter((proposal) => proposal.day === day)
      .sort((a, b) => b.voting_points - a.voting_points)[0];
    const mealId = locked?.meal_id ?? leadingProposal?.meal_id ?? "";
    return {
      day,
      locked,
      proposal: leadingProposal,
      meal: meals[mealId]
    };
  });
  const todayDayKey = new Date().toLocaleDateString("en-US", { weekday: "long" }).toLowerCase();
  const selectedEntry = menuEntries.find((entry) => entry.day === selectedDay) ?? menuEntries[0];
  const todayEntry = menuEntries.find((entry) => entry.day === todayDayKey) ?? selectedEntry;
  const selectedMealDetails = selectedEntry?.meal
    ? mealDisplayDetails[selectedEntry.meal.id] ?? {
        ingredients: selectedEntry.meal.tags,
        calories: 600,
        protein: selectedEntry.meal.protein_type === "vegetarian" ? 22 : 34,
        bit: "Chef notes currently written in gravy."
      }
    : {
        ingredients: ["mystery", "hope", "timer confidence"],
        calories: 0,
        protein: 0,
        bit: "The kitchen is still negotiating with the calendar."
      };
  const selectedChefIds = selectedEntry?.locked?.chef ?? selectedEntry?.proposal?.chef_volunteers ?? [];
  const selectedCleanerIds = selectedEntry?.locked?.cleanup ?? selectedEntry?.proposal?.cleanup_volunteers ?? [];
  const isSelectedToday = selectedEntry?.day === todayEntry?.day;

  return (
    <main className={`display-shell ${theme.className}`}>
      <section className="display-menu">
        <header className="display-menu-header">
          <div>
            <p className="display-kicker">{theme.label}</p>
            <h1>{theme.venue}</h1>
          </div>
          <div className="display-meta">
            <span>{today}</span>
            <strong>{session.join_code}</strong>
          </div>
        </header>

        <div className="display-week-nav" aria-label="Displayed week">
          <button type="button" onClick={() => loadSavedWeekForOffset(displayWeekOffset - 1)}>
            <ChevronLeft size={18} /> Previous Week
          </button>
          <div>
            <strong>{displayWeekLabel}</strong>
            <span>{displayWeekRange}</span>
            {defaultWeekOffset > 0 && displayWeekOffset === defaultWeekOffset && <small>Planning week</small>}
          </div>
          <button type="button" onClick={() => loadSavedWeekForOffset(0)} disabled={displayWeekOffset === 0}>
            Current Week
          </button>
          <button type="button" onClick={() => loadSavedWeekForOffset(displayWeekOffset + 1)}>
            Next Week <ChevronRight size={18} />
          </button>
        </div>

        <div className="display-ornament" aria-hidden="true">
          <span />
        </div>

        <div className="display-subhead">
          <span>{theme.tagline}</span>
          <span>{phaseLabel}</span>
        </div>

        <div className="display-landscape-board">
          {selectedEntry && (
            <section className="display-today-feature">
              {isSelectedToday
                ? <span className="display-badge">{theme.badgeLabel}</span>
                : <p className="display-kicker">{dayLabel(selectedEntry.day)} {theme.detailsWord}</p>}
              <div className="display-today-dish">
                <span className="display-emoji">{selectedEntry.meal?.emoji ?? "?"}</span>
                <div>
                  <small>{dayLabel(selectedEntry.day)}</small>
                  <h2>{selectedEntry.meal?.name ?? "Chef's choice"}</h2>
                  <p>{selectedMealDetails.bit}</p>
                </div>
              </div>
              <div className="display-today-crew">
                <div>
                  <small>{theme.crewLabels.cook}</small>
                  <div className="display-avatar-row">
                    {selectedChefIds.length
                      ? selectedChefIds.map((id) => (
                          <span className="display-person-chip" key={`selected-chef-${id}`}>
                            <b>{session.players[id]?.avatar ?? "?"}</b>
                            {session.players[id]?.name ?? "Unassigned"}
                          </span>
                        ))
                      : <span className="display-person-chip muted-chip"><b>?</b> Unassigned</span>}
                  </div>
                </div>
                <div>
                  <small>{theme.crewLabels.clean}</small>
                  <div className="display-avatar-row">
                    {selectedCleanerIds.length
                      ? selectedCleanerIds.map((id) => (
                          <span className="display-person-chip" key={`selected-cleaner-${id}`}>
                            <b>{session.players[id]?.avatar ?? "?"}</b>
                            {session.players[id]?.name ?? "Unassigned"}
                          </span>
                        ))
                      : <span className="display-person-chip muted-chip"><b>?</b> Unassigned</span>}
                  </div>
                </div>
              </div>
              <div className="display-nutrition">
                <span>{selectedMealDetails.calories} {theme.nutritionLabels.calories}</span>
                <span>{selectedMealDetails.protein}g {theme.nutritionLabels.protein}</span>
              </div>
              <div className="display-ingredients">
                {selectedMealDetails.ingredients.map((ingredient) => (
                  <span key={`selected-${ingredient}`}>{ingredient}</span>
                ))}
              </div>
            </section>
          )}

          <section className="display-week-panel">
            <div className="display-menu-grid">
              {menuEntries.map(({ day, locked, proposal, meal }) => (
                <button
                  aria-expanded={selectedDay === day}
                  className={[
                    "display-menu-item",
                    locked ? "locked" : "",
                    day === todayEntry?.day ? "today" : "",
                    selectedDay === day ? "selected" : ""
                  ].filter(Boolean).join(" ")}
                  key={day}
                  onClick={() => setSelectedDay(day)}
                  type="button"
                >
                  <div className="display-day">
                    <span>{dayLabel(day)}</span>
                    <small>
                      {day === todayEntry?.day
                        ? theme.dayStatusLabels.today
                        : locked
                          ? theme.dayStatusLabels.reserved
                          : proposal
                            ? theme.dayStatusLabels.leading
                            : theme.dayStatusLabels.open}
                    </small>
                  </div>
                  <div className="display-dish">
                    <span>{meal?.emoji ?? "?"}</span>
                    <div>
                      <strong>{meal?.name ?? "Chef's choice"}</strong>
                      <p>
                        {locked
                          ? `${locked.chef.map((id) => session.players[id]?.name).join(", ") || "Unassigned"} cooks`
                          : proposal
                            ? `${proposal.voting_points} points on the board`
                            : "Waiting for the family draft"}
                      </p>
                    </div>
                  </div>
                  <div className="display-mini-crew" aria-label={`${titleCase(day)} crew`}>
                    {(locked?.chef ?? proposal?.chef_volunteers ?? []).slice(0, 2).map((id) => (
                      <span title={`${session.players[id]?.name ?? "Someone"} cooks`} key={`chef-${day}-${id}`}>
                        {session.players[id]?.avatar ?? "?"}
                      </span>
                    ))}
                    {(locked?.cleanup ?? proposal?.cleanup_volunteers ?? []).slice(0, 2).map((id) => (
                      <span title={`${session.players[id]?.name ?? "Someone"} cleans`} key={`clean-${day}-${id}`}>
                        {session.players[id]?.avatar ?? "?"}
                      </span>
                    ))}
                    <Info size={14} aria-hidden="true" />
                  </div>
                </button>
              ))}
            </div>
          </section>
        </div>

        <footer className="display-footer">
          <span>{session.id === "mock-week" ? theme.statusLabels.mock : theme.statusLabels.live}</span>
          <span>{theme.footerHint}</span>
        </footer>

        {!forcedTheme && activeMenuThemes.length > 1 && (
          <button
            type="button"
            className="display-theme-switch"
            onClick={advanceTheme}
            aria-label="Show next menu style"
          >
            <ChevronRight size={20} />
          </button>
        )}
      </section>
    </main>
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
  const [pickedFromDay, setPickedFromDay] = useState<string | null>(null);
  const [canDrag] = useState(() => window.matchMedia("(pointer: fine)").matches);
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
    setPickedFromDay(null);
  }

  function moveMeal(fromDay: string, toDay: string) {
    setAssigned((current) => {
      const movingMealId = current[fromDay];
      const replacedMealId = current[toDay];
      return { ...current, [fromDay]: replacedMealId, [toDay]: movingMealId };
    });
  }

  function pickFromRail(mealId: string) {
    setPickedMealId((current) => (current === mealId ? "" : mealId));
    setPickedFromDay(null);
  }

  function pickAssigned(day: string, mealId: string) {
    if (pickedMealId === mealId && pickedFromDay === day) {
      setPickedMealId("");
      setPickedFromDay(null);
      return;
    }
    setPickedMealId(mealId);
    setPickedFromDay(day);
  }

  function placeOnDay(day: string) {
    if (!pickedMealId) return;
    if (pickedFromDay) {
      if (pickedFromDay !== day) moveMeal(pickedFromDay, day);
      setPickedMealId("");
      setPickedFromDay(null);
      return;
    }
    assignMeal(day, pickedMealId);
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
                draggable={canDrag}
                onClick={() => pickFromRail(meal.id)}
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
                onClick={() => placeOnDay(day)}
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
                  <div
                    className={pickedMealId === mealId && pickedFromDay === day ? "slot-meal picked" : "slot-meal"}
                    draggable={canDrag}
                    onDragStart={(event) => event.dataTransfer.setData("text/plain", `day:${day}`)}
                    onClick={(event) => {
                      event.stopPropagation();
                      pickAssigned(day, mealId!);
                    }}
                  >
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
  onUnlock,
  onGeneralAssembly,
  onComplete
}: {
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  onVote: (proposalId: string, kind: "support" | "withdraw" | "downvote") => void;
  onPlayCard: (payload: { card: string; proposal_id?: string; day?: string; target_day?: string; meal_id?: string }) => void;
  onPass: () => void;
  onLock: (day: string, proposalId: string) => void;
  onUnlock: (day: string) => void;
  onGeneralAssembly: (ruleId: string, points: number) => void;
  onComplete: () => void;
}) {
  const currentTurnId = session.turn_order[session.current_turn_index % Math.max(1, session.turn_order.length)];
  const currentTurnPlayer = currentTurnId ? session.players[currentTurnId] : undefined;
  const isYourTurn = currentTurnId === playerId;
  const myPointsRemaining = session.player_state[playerId]?.voting_points_remaining ?? 0;

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
        {session.rules.map((rule) => {
          const contributions = session.general_assembly[rule.id] ?? {};
          const totalPoints = Object.values(contributions).reduce((sum, value) => sum + value, 0);
          const myContribution = contributions[playerId] ?? 0;
          return (
            <div key={rule.id} className={rule.satisfied ? "rule ok" : "rule warn"}>
              <strong>{rule.satisfied ? "OK" : "Rule"}</strong>
              <span>{rule.label}</span>
              {!rule.satisfied && rule.level === "HOUSE" && (
                <div className="general-assembly">
                  <small>
                    General Assembly: {totalPoints}/{session.general_assembly_threshold} points
                    {myContribution > 0 ? ` · you gave ${myContribution}` : ""}
                  </small>
                  <button disabled={myPointsRemaining < 1} onClick={() => onGeneralAssembly(rule.id, 1)}>
                    <Plus size={14} /> Support Exception
                  </button>
                </div>
              )}
            </div>
          );
        })}
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
            onUnlock={onUnlock}
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
  onLock,
  onUnlock
}: {
  day: string;
  session: Session;
  meals: Record<string, Meal>;
  playerId: string;
  disabled: boolean;
  onVote: (proposalId: string, kind: "support" | "withdraw" | "downvote") => void;
  onPlayCard: (payload: { card: string; proposal_id?: string; day?: string; target_day?: string; meal_id?: string }) => void;
  onLock: (day: string, proposalId: string) => void;
  onUnlock: (day: string) => void;
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
          <button className="unlock-button" onClick={() => onUnlock(day)}>
            Unlock
          </button>
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
          <b><img src={uiAssets.votingPoint} alt="" aria-hidden="true" />{proposal.voting_points}</b>
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
        <strong className="proposal-score"><img src={uiAssets.votingPoint} alt="" aria-hidden="true" />{proposal.voting_points}</strong>
        <button disabled={disabled} aria-label="Support proposal" onClick={() => onVote(proposal.id, "support")}>
          <img className="heart-icon" src={uiAssets.heart} alt="" aria-hidden="true" />
          <Plus size={14} />
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
  const { year, week } = getDisplayWeek();
  const savedWeekId = `${year}-W${String(week).padStart(2, "0")}`;
  const [saved, setSaved] = useState(() => {
    const savedWeeks = JSON.parse(localStorage.getItem(SAVED_WEEKS_KEY) ?? "{}") as Record<string, { session_id?: string }>;
    return savedWeeks[savedWeekId]?.session_id === session.id;
  });
  const [saveStatus, setSaveStatus] = useState("");

  function buildLocalSavedWeek(savedAt = new Date().toISOString()) {
    return {
      id: savedWeekId,
      saved_at: savedAt,
      session_id: session.id,
      join_code: session.join_code,
      week,
      year,
      days: session.days,
      plan: Object.fromEntries(
        session.days.map((day) => {
          const entry = session.week[day];
          return [
            day,
            entry
              ? {
                  meal_id: entry.meal_id,
                  meal_name: meals[entry.meal_id]?.name ?? entry.meal_id,
                  meal_emoji: meals[entry.meal_id]?.emoji ?? "",
                  chef: entry.chef.map((id) => session.players[id]?.name ?? id),
                  cleanup: entry.cleanup.map((id) => session.players[id]?.name ?? id),
                  rule_exceptions: entry.rule_exceptions
                }
              : null
          ];
        })
      ),
      rule_overrides: session.rule_overrides
    };
  }

  function cacheSavedWeek(savedWeek: unknown) {
    const savedWeeks = JSON.parse(localStorage.getItem(SAVED_WEEKS_KEY) ?? "{}") as Record<string, unknown>;
    savedWeeks[savedWeekId] = savedWeek;
    localStorage.setItem(SAVED_WEEKS_KEY, JSON.stringify(savedWeeks));
  }

  async function saveWeek() {
    setSaveStatus("");
    try {
      const savedWeek = await api.saveWeek(session.id, year, week);
      cacheSavedWeek(savedWeek);
      setSaveStatus("Saved to Forkcast server");
    } catch (err) {
      cacheSavedWeek(buildLocalSavedWeek());
      setSaveStatus("Saved on this phone only");
    }
    setSaved(true);
  }

  return (
    <section className="stage final">
      <div className="final-header">
        <div>
          <p className="eyebrow">The Forkcast Is In</p>
          <h2>Dinner is decided</h2>
          <p className="week-badge">Week {week} · {year}</p>
        </div>
        <button className={saved ? "save-week-button saved" : "save-week-button"} onClick={saveWeek}>
          {saved ? <Check size={18} /> : <Save size={18} />}
          {saved ? "Saved" : "Save Week"}
        </button>
        {saveStatus && <p className="save-status">{saveStatus}</p>}
      </div>
      {session.rule_overrides.length > 0 && (
        <div className="turn-log">
          {session.rule_overrides.map((ruleId) => (
            <p key={ruleId}>
              General Assembly Exception: {session.rules.find((rule) => rule.id === ruleId)?.label ?? ruleId}
            </p>
          ))}
        </div>
      )}
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
