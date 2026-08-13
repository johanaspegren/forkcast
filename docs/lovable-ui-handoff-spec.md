# Forkcast UI Handoff Spec for Lovable

This document is the design and integration brief for rebuilding the Forkcast UI in Lovable, then bringing the result back into this repo with minimal wiring.

Forkcast is a mobile-first family dinner planning game. The backend is authoritative and already exists. The new UI should be a React + TypeScript presentation layer that renders the current session state and calls injected action handlers.

## Product Intent

Forkcast should feel like a small family board game on a phone, not like a meal planner form.

The experience should be playful, quick to scan, and easy for children and adults to use around the table. The UI should make negotiation feel visible: who wants what, which meal is leading, whose turn it is, how many Voting Points remain, and what still blocks a day from being locked.

Core tone:

- Warm, social, family dinner energy.
- Game-like controls and feedback.
- Mobile-first, touch-first, fast to understand.
- Clear enough that a player can join mid-session and know what to do.
- Avoid a generic SaaS/dashboard look.
- a little fun and smart works, as in popcult-references

## Existing Tech Constraints

Keep these constraints unless this repo changes:

- React 19
- TypeScript
- Vite
- CSS modules, plain CSS, or Tailwind-style generated classes are all acceptable if easy to import
- Icons should use `lucide-react` where possible
- No new backend
- No client-side game rule engine
- No client-side persistence beyond the current player id in `localStorage`
- Backend data is received via REST and WebSocket

The existing backend owns all official state transitions. The UI sends user intent and renders the returned `Session`.

## Recommended Integration Shape

Design the Lovable output as a replaceable UI package with a single top-level component:

```tsx
export function ForkcastGameUI(props: ForkcastGameUIProps) {
  // render all non-display phone UI states
}
```

Preferred file layout when importing back:

```text
src/ui/lovable/ForkcastGameUI.tsx
src/ui/lovable/components/*.tsx
src/ui/lovable/styles.css
```

The current `src/App.tsx` should keep owning data loading, WebSocket subscription, routing, and calls to `src/api/rest.ts`. The Lovable UI should receive data and callbacks through props.

Do not hard-code `fetch()` calls inside the Lovable UI if possible. Use injected action handlers. This keeps the UI portable and prevents duplicate API wiring.

## Top-Level UI Props

Use this contract for the replacement phone UI:

```ts
import type { Meal, SchoolMenu, Session } from "../../game/gameTypes";

export type VoteKind = "support" | "withdraw" | "downvote";

export type PlayCardPayload = {
  card: string;
  proposal_id?: string;
  day?: string;
  target_day?: string;
  meal_id?: string;
};

export type ForkcastGameUIProps = {
  session: Session | null;
  meals: Meal[];
  mealById: Record<string, Meal>;
  schoolMenu: SchoolMenu | null;
  currentPlayerId: string;
  error: string;
  isBusy?: boolean;

  joinForm: {
    name: string;
    joinCode: string;
    mealSuggestionCount: number;
    onNameChange: (value: string) => void;
    onJoinCodeChange: (value: string) => void;
    onMealSuggestionCountChange: (value: number) => void;
    onCreateSession: () => void;
    onCreateSimulation: () => void;
    onJoinSession: () => void;
  };

  actions: {
    onStart: () => void;
    onAddSimulatedPlayers: () => void;
    onSimulateNext: () => void;
    onSelectMeals: (mealIds: string[]) => void;
    onPlaceMeals: (placements: Array<{ meal_id: string; day: string; points: number }>) => void;
    onContinueReveal: () => void;
    onVote: (proposalId: string, kind: VoteKind) => void;
    onPlayCard: (payload: PlayCardPayload) => void;
    onPassTurn: () => void;
    onLockDay: (day: string, proposalId: string, ruleExceptions?: string[]) => void;
    onUnlockDay: (day: string) => void;
    onGeneralAssembly: (ruleId: string, points: number) => void;
    onComplete: () => void;
  };
};
```

If Lovable cannot preserve this exact structure, keep the same semantic split:

- `session`, `meals`, `schoolMenu`, `currentPlayerId`, `error`
- all user actions as callbacks
- no direct backend logic inside presentational components

## Existing Data Model

These types already exist in `src/game/gameTypes.ts`. Lovable can duplicate them during design, but the returned UI should import the real types from this repo.

```ts
export type GamePhase =
  | "LOBBY"
  | "MEAL_SELECTION"
  | "SECRET_PLACEMENT"
  | "REVEAL"
  | "NEGOTIATION"
  | "FINAL_VOTE"
  | "COMPLETE";

export type Meal = {
  id: string;
  name: string;
  emoji: string;
  tags: string[];
  protein_type: string | null;
  minced_meat: boolean;
  fish: boolean;
};

export type Player = {
  id: string;
  name: string;
  avatar: string;
  favourite_meals: string[];
  simulated: boolean;
};

export type Proposal = {
  id: string;
  meal_id: string;
  day: string;
  owners: string[];
  voting_points: number;
  supporters: string[];
  support_points: Record<string, number>;
  downvote_points: Record<string, number>;
  downvotes: number;
  status: "ACTIVE" | "LOCKED";
  chef_volunteers: string[];
  cleanup_volunteers: string[];
};

export type PlayerSession = {
  player_id: string;
  voting_points_remaining: number;
  meal_cards: string[];
  action_cards: string[];
  action_cards_played: string[];
  cook_commitments: string[];
  clean_commitments: string[];
  selected_meals: string[];
  placed: boolean;
};

export type WeekEntry = {
  meal_id: string;
  chef: string[];
  cleanup: string[];
  rule_exceptions: string[];
};

export type RuleStatus = {
  id: string;
  label: string;
  level: string;
  satisfied: boolean;
  detail: string;
};

export type Session = {
  id: string;
  join_code: string;
  phase: GamePhase;
  days: string[];
  players: Record<string, Player>;
  player_state: Record<string, PlayerSession>;
  proposals: Record<string, Proposal>;
  week: Record<string, WeekEntry | null>;
  rules: RuleStatus[];
  turn_order: string[];
  current_turn_index: number;
  turn_log: string[];
  max_players: number;
  starting_voting_points: number;
  max_selected_meals: number;
  max_action_cards_played: number;
  rule_overrides: string[];
  general_assembly: Record<string, Record<string, number>>;
  general_assembly_threshold: number;
};
```

## API Contract

The Lovable UI should not call these endpoints directly in final integration, but these are the authoritative operations behind the injected callbacks.

Base paths are same-origin:

```text
GET  /api/meals
GET  /api/school-menu?url=<encoded-url>
POST /api/sessions
GET  /api/sessions/:sessionId
POST /api/sessions/:sessionId/join
POST /api/sessions/:sessionId/simulate/add-players
POST /api/sessions/:sessionId/simulate/next
POST /api/sessions/:sessionId/start
POST /api/sessions/:sessionId/meal-selection
POST /api/sessions/:sessionId/placement
POST /api/sessions/:sessionId/reveal/continue
POST /api/sessions/:sessionId/vote
POST /api/sessions/:sessionId/cards/play
POST /api/sessions/:sessionId/pass-turn
POST /api/sessions/:sessionId/lock-day
POST /api/sessions/:sessionId/general-assembly
POST /api/sessions/:sessionId/unlock-day
POST /api/sessions/:sessionId/complete
```

WebSocket:

```text
WS /ws/sessions/:sessionId
```

Message shape:

```json
{
  "event": "SESSION_UPDATED",
  "session": {}
}
```

Every successful REST mutation returns the full updated `Session`.

## Screens and States

### Join / Create

Shown when there is no active session/current player.

Required controls:

- Player name input
- Meal suggestions count selector, values 2, 3, 4, 5
- Create Session
- Create Simulation
- Session ID input
- Join Session
- Error message area

Design goals:

- First viewport must clearly say Forkcast.
- The main actions should be thumb-friendly.
- Simulation should look like a development/demo option, not the main path.

### Lobby

Phase: `LOBBY`

Required information:

- Session id / join code
- Share URL or QR code area
- Player list with avatars and names
- Capacity indicator, for example 2 / 4

Required controls:

- Add 3 simulated players, only if there is room and no simulated players yet
- Start Meal Draft

### Meal Selection / Secret Placement

Current code treats the active planning screen as the place where a player assigns selected meals to days and spends initial Voting Points.

Phases:

- `MEAL_SELECTION`
- `SECRET_PLACEMENT`

Required information:

- Current player
- Voting Points remaining
- Number of suggestions required: `session.max_selected_meals`
- Days in `session.days`
- Available meals
- Optional school lunch context if `schoolMenu` exists

Required controls:

- Filter meals by favourites and other useful categories
- Assign meals to days
- Move assigned meals between days
- Remove assigned meal from a day
- Add or remove points per placed meal
- Submit Suggestions

Submit payload:

```ts
Array<{ meal_id: string; day: string; points: number }>
```

Validation:

- Exactly `session.max_selected_meals` meals should be assigned before submit.
- Total spent points cannot exceed `player_state[currentPlayerId].voting_points_remaining`.
- A player should not assign the same meal to multiple days.

### Reveal

Phase: `REVEAL`

Required information:

- Each day and all revealed proposals
- Meal name, emoji, proposer names, and current points

Required control:

- Continue to negotiation

Design goal:

- This should feel like cards being revealed after secret placement.

### Negotiation Board

Phase: `NEGOTIATION`

Required information:

- Current turn player
- Whether it is your turn
- Voting Points remaining
- House rules and whether each is satisfied
- General Assembly progress for unsatisfied house rules
- One column or stacked section per day
- Proposals sorted by `voting_points` descending
- Locked days
- Turn log

Required controls:

- Pass Turn
- Support proposal
- Withdraw own support if already supporting
- Downvote proposal if not supporting
- Volunteer/un-volunteer to cook with card `ILL_COOK`
- Volunteer/un-volunteer to clean with card `ILL_CLEAN`
- Lock a day
- Unlock a day
- Support a General Assembly exception

Important rules for controls:

- Proposal interaction should be disabled unless it is the player's turn and phase is `NEGOTIATION`.
- A proposal can be locked when it is the leading proposal for its day and has at least one cook volunteer and at least one cleanup volunteer.
- If the proposal is leading but chores are missing, show the missing requirement.
- If it is not leading, show that it cannot be locked yet.

Vote callbacks:

```ts
onVote(proposal.id, "support")
onVote(proposal.id, "withdraw")
onVote(proposal.id, "downvote")
```

Chore callbacks:

```ts
onPlayCard({ card: "ILL_COOK", proposal_id: proposal.id })
onPlayCard({ card: "ILL_CLEAN", proposal_id: proposal.id })
```

Lock callback:

```ts
onLockDay(day, proposal.id)
```

General Assembly callback:

```ts
onGeneralAssembly(rule.id, 1)
```

### Final Vote / Complete

Phases:

- `FINAL_VOTE`
- `COMPLETE`

Required information:

- Final week plan by day
- Meal names and emoji
- Chef volunteers
- Cleanup volunteers
- Any General Assembly exceptions
- Remaining unsatisfied rules if present

Required control:

- In `FINAL_VOTE`, show Final Forkcast / Complete action.
- In `COMPLETE`, show the final plan as read-only.

## Components to Design

Minimum recommended component set:

- `ForkcastGameUI`
- `JoinCreateScreen`
- `LobbyScreen`
- `PlanningScreen`
- `RevealScreen`
- `NegotiationScreen`
- `FinalForkcastScreen`
- `VotingPointBank`
- `PlayerChip`
- `MealCard`
- `DayLane`
- `ProposalCard`
- `RuleStrip`
- `TurnBanner`
- `SchoolLunchStrip`
- `ErrorBanner`

Keep business logic thin and local to display state. For example, sorting proposals and calculating whether a day can be locked is acceptable. Deciding official game outcomes is not.

## Visual Design Direction

Use a distinct game identity:

- App name: Forkcast
- Theme: weekly dinner draft / family negotiation game
- Visual language: meal cards, day lanes, table tokens, Voting Points, avatars
- Corners: 8px or less for cards and controls
- Text: compact and scannable on phone
- Buttons: use icons where possible, especially plus, minus, check, users, bot, lock, unlock, chef/cooking, fast-forward

Avoid:

- Large marketing hero sections after the join screen
- Nested cards inside cards
- Decorative gradient blobs or one-note color palettes
- Overly dark UI
- Tiny tap targets
- Controls that move around as text changes

Mobile layout guidance:

- Target 390px wide first.
- All primary controls should be usable one-handed.
- Keep bottom actions sticky or visually anchored when a phase has a clear next action.
- Use horizontal scroll only for card rails, not for the main week board if it hurts readability.
- Text must not overflow buttons or chips.

Desktop layout guidance:

- Keep phone-game proportions centered or use a wider board only if it improves negotiation scanning.
- Do not turn the app into a dashboard.

## Hallway Display

The repo also has a tablet display at:

```text
/display?session=<session-id>
/display?mock=1
```

The first Lovable pass can ignore the hallway display unless explicitly designing it. If it is redesigned, keep it as a separate read-only route/component. It should not expose game actions.

## Mock Data for Lovable

Use this minimal mock shape to design all phases. Values can be expanded for visual richness.

```ts
export const mockMeals = [
  { id: "salmon", name: "Lemon Salmon", emoji: "🐟", tags: ["fish", "quick"], protein_type: "fish", minced_meat: false, fish: true },
  { id: "tacos", name: "Taco Night", emoji: "🌮", tags: ["minced", "family"], protein_type: "beef", minced_meat: true, fish: false },
  { id: "pasta", name: "Pesto Pasta", emoji: "🍝", tags: ["quick", "vegetarian"], protein_type: "vegetarian", minced_meat: false, fish: false },
  { id: "chicken_curry", name: "Chicken Curry", emoji: "🍛", tags: ["chicken", "spiced"], protein_type: "chicken", minced_meat: false, fish: false },
  { id: "pizza", name: "Friday Pizza", emoji: "🍕", tags: ["weekend", "family"], protein_type: "mixed", minced_meat: false, fish: false }
];
```

Mock sessions should cover:

- no session
- lobby with 1-4 players
- planning phase for a current player
- reveal with several proposals per day
- negotiation with one locked day, one leading proposal missing chores, and one unsatisfied house rule
- complete week

## Import Checklist

When bringing Lovable results back into this repo:

1. Copy the generated UI files into `src/ui/lovable/`.
2. Replace duplicated mock types with imports from `src/game/gameTypes.ts`.
3. Move or import the generated CSS from `src/ui/lovable/styles.css`.
4. Adapt `src/App.tsx` so it passes the current state and callbacks into `ForkcastGameUI`.
5. Keep `src/api/rest.ts` and `src/api/websocket.ts` as the only backend integration layer.
6. Run `npm run build`.
7. Run backend and frontend, create a simulation, and test all phases.

Expected local commands:

```bash
npm run build
npm run backend
npm run dev
```

## Acceptance Criteria

The imported UI is ready when:

- A player can create a session.
- A player can join an existing session.
- Lobby shows players and can start.
- A player can place exactly the required number of meals and spend points.
- Reveal shows proposals grouped by day.
- Negotiation supports vote, withdraw, downvote, cook, clean, pass, lock, unlock, and General Assembly actions.
- Final Forkcast shows the completed week.
- WebSocket updates from other players update the visible UI without refresh.
- Mobile width around 390px has no overlapping text or unusable controls.
- `npm run build` passes.

## Prompt to Paste into Lovable

Build a React + TypeScript mobile-first game UI for Forkcast, a family dinner planning game. Use the design brief, data model, props contract, screens, and acceptance criteria from this document. The UI must render from a `Session` object and call injected callbacks for all actions. Do not create a backend and do not hard-code fetch calls. Produce a polished, playful phone-game interface with components that can be copied into `src/ui/lovable/` in a Vite React app.
