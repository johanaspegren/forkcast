# Forkcast
## Mobile Family Dinner Planning Game — v1 Specification

### 1. Concept

**Forkcast** is a multiplayer family dinner-planning game.

Family members join a weekly planning session from their phones. Each player proposes meals, spends a limited pool of Voting Points, plays action cards, forms coalitions around common choices, volunteers for cooking or washing up, and negotiates exceptions to household rules.

At the end of the session, Forkcast produces a dinner plan for the coming week together with assigned chefs and chores.

The goal is not to produce a single “winner”. The goal is to make weekly dinner planning entertaining enough that the family actually wants to participate.

Forkcast should feel more like a small social board game than a meal-planning form.

---

# 2. Technical concept

## Frontend

Mobile-first React web application.

Primary target:

- iPhone
- Android phones
- tablet browsers
- desktop browser for development

The interface should behave like a mobile game rather than a traditional responsive website.

Recommended initial stack:

- React
- TypeScript
- Vite
- CSS or lightweight component system
- WebSocket connection to backend for live game state

No native mobile application is required for v1.

The web app runs from the LAN server and players access it using something similar to:

`http://forkcast.local`

A session can then be joined with a short code or QR code.

---

# 3. Backend

Python server running continuously on the home LAN.

Recommended stack:

- Python
- FastAPI
- WebSockets
- Pydantic
- SQLite initially
- optional Ollama/local-LLM integration

The backend is authoritative.

Clients should never independently calculate the official game result. They send actions to the backend and receive the resulting state.

This makes multiplayer synchronisation considerably less exciting than debugging four disagreeing phones, which is desirable.

Example deployment:

```text
Home LAN

                 ┌──────────────────┐
                 │ Forkcast Server  │
                 │ Python/FastAPI   │
                 │                  │
                 │ Game Engine      │
                 │ SQLite           │
                 │ AI Services      │
                 └────────┬─────────┘
                          │
               WebSocket / REST
                          │
          ┌───────────────┼───────────────┐
          │               │               │
      Johan Phone      Anna Phone      Kid Phone
          │
          └──────── Kitchen tablet later
```

---

# 4. Design principles

Forkcast should follow five principles.

## 4.1 Planning is the game

Do not build a meal planner and then add game elements.

The game itself should create the meal plan.

## 4.2 Positive behaviour should be cheaper

Supporting something another family member wants should generally cost less than blocking something.

## 4.3 Contribution creates power

Cooking and taking chores should create additional Voting Points.

More responsibility means more influence.

## 4.4 Rules guide rather than dominate

House rules should shape the week, but the family can democratically override them through a General Assembly.

True safety constraints cannot be overridden.

## 4.5 AI assists but does not run the game

Forkcast must work perfectly without an LLM.

AI can enhance:

- meal matching
- compromises
- recipe transformations
- school-menu interpretation
- meal suggestions

but game rules must remain deterministic.

---

# 5. Core concepts

There are five major game objects.

### Meal Cards

Things the family could eat.

Examples:

- Yakiniku
- Tacos
- Salmon
- Tomato Soup
- Chicken Curry
- Pizza
- Pasta

### Voting Points

The single game currency.

Players spend Voting Points to influence the week.

### Action Cards

Special actions that alter the planning process.

### House Rules

Constraints describing what constitutes an acceptable week.

### Weekly Board

The Monday–Sunday dinner schedule being constructed.

---

# 6. Players

Each family member has a persistent profile.

Example:

```json
{
  "id": "johan",
  "name": "Johan",
  "avatar": "avatar_01",
  "favourite_meals": [
    "yakiniku",
    "salmon",
    "tacos"
  ]
}
```

Profile information can eventually contain:

- name
- avatar
- favourite meals
- disliked meals
- dietary restrictions
- allergies
- spice preference
- preferred cooking days
- cooking ability
- historic cooking statistics

Only name, avatar and favourites are required for v1.

---

# 7. Weekly game session

A Forkcast session represents one week.

Example:

```text
Forkcast Week 34

Players:
Johan
Anna
Elsa
Oscar

Planning:
Monday
Tuesday
Wednesday
Thursday
Friday
```

The number of planning days should be configurable.

Five weekdays is a good initial default.

---

# 8. Game flow

The initial game state machine should be:

```text
LOBBY
  ↓
MEAL_SELECTION
  ↓
SECRET_PLACEMENT
  ↓
REVEAL
  ↓
NEGOTIATION
  ↓
RULE_RESOLUTION
  ↓
FINAL_VOTE / LOCKING
  ↓
COMPLETE
```

---

# 9. Lobby

One player creates a session.

The server generates:

- session ID
- join code
- optional QR URL

Example:

```text
FORKCAST
Weekly Dinner Draft

Join code:

FORK-42

3 / 4 players joined
```

Players joining see avatars appear in real time.

Host starts the session.

---

# 10. Starting resources

Suggested first balancing values:

Each player receives:

**10 Voting Points**

and:

**3 Action Cards**

These values should be configuration values rather than hard-coded game logic.

---

# 11. Meal selection

Each player privately selects approximately three Meal Cards.

Example:

Johan selects:

- Yakiniku
- Salmon
- Tacos

These are hidden until the reveal phase.

Meals should come primarily from the player's favourites.

Forkcast may also show:

- family favourites
- recent meals
- suggested meals
- new meals

For v1, simply selecting three favourites is sufficient.

---

# 12. Secret placement

Players place Meal Cards onto preferred days.

Example:

```text
Monday
Tacos
+2 Voting Points

Wednesday
Salmon
+0

Thursday
Yakiniku
+4
```

These choices remain hidden from other players until everyone submits.

A player may choose to attach Voting Points to proposals.

---

# 13. Reveal

When all players submit, Forkcast reveals all proposals simultaneously.

This should be a visually important game moment.

Example:

```text
MONDAY

🌮 Tacos           Johan       2
🥣 Tomato Soup     Anna        2
🍕 Pizza           Oscar       4
```

The central server identifies:

- identical meal proposals
- similar meal proposals
- obvious conflicts
- currently leading candidates

---

# 14. Voting Points

Voting Points are the only numerical player currency.

Suggested initial costs:

### Support someone else's meal

Cost:

**1 Voting Point**

### Strengthen your own meal

Cost:

**2 Voting Points per boost**

### Downvote a meal

Cost:

**3 Voting Points**

The exact balancing should be configurable and tested through play.

The intentional asymmetry is important:

Helping another person should be cheap.

Preventing another person getting what they want should be expensive.

---

# 15. Voting Points are weekly

Voting Points do not refresh each evening.

A player has one budget for the entire planning session.

Example:

```text
Voting Points remaining

Johan: 4
Anna: 7
Elsa: 2
Oscar: 6
```

This creates strategic decisions.

A player may spend heavily to secure one particular meal, but then have little influence over the rest of the week.

---

# 16. Coalition mechanic

When multiple people choose the same meal, their existing support is combined automatically.

Example:

```text
Johan:
Salmon +2

Elsa:
Salmon +3

Result:

SALMON
5 Voting Points
2 supporters
```

No points are lost.

## Similar-meal coalition

Forkcast may also detect meals that could reasonably be merged.

Example:

```text
Yakiniku

Teriyaki Chicken

Japanese Beef Bowl
```

Forkcast can propose:

```text
COALITION AVAILABLE

Japanese Bowl Night

Merge proposals?
```

Both players must agree.

If accepted, all Voting Points from the participating proposals are transferred to the coalition meal.

AI may later help suggest compromises.

For v1, identical meals should merge automatically.

Similarity-based coalitions may initially require manual selection.

---

# 17. Action Cards

Each player begins a session with a small random hand of Action Cards.

Recommended:

**3 cards drawn**

Maximum:

**2 played per session**

This prevents cards overwhelming the underlying voting game.

---

# 18. Forkcast v1 Action Deck

## 🎰 Roulette

Select an unresolved night.

Forkcast randomly chooses an eligible meal.

The player invoking Roulette commits to the result.

Rejecting the result costs Voting Points.

Suggested penalty:

**−2 Voting Points**

Roulette respects hard restrictions.

House preferences may be ignored.

---

## 🔄 Swap

Move a proposed meal from one day to another.

Swap must not destroy the meal.

Example:

```text
Chicken Curry
Thursday → Tuesday
```

The proposal owner may need to approve the destination.

---

## 👨‍🍳 I'll Cook

Player commits to being chef for a specific night.

Reward:

Suggested:

**+2 Voting Points**

The points should only become available once the cooking commitment is locked.

This avoids repeatedly volunteering for hypothetical meals simply to manufacture Voting Points.

---

## 🧽 I'll Clean

Player commits to washing up / kitchen cleanup.

Suggested reward:

**+1 Voting Point**

Again, the chore must become part of the locked schedule.

---

## 🤝 Coalition

Allows two compatible but non-identical Meal Cards to be merged.

Both owners must accept.

All existing Voting Points follow into the coalition proposal.

Example:

```text
Yakiniku 3
+
Teriyaki Bowl 2

↓

Japanese Beef Bowl 5
```

---

## 🔥 Spice It Up

Modify the selected meal toward a spicier variant.

Example:

```text
Chicken Curry
→
Hot Thai-style Chicken Curry
```

This changes the meal variant rather than its fundamental identity.

---

## 🥦 Veg It Up

Modify the meal to include more vegetables.

Example:

```text
Tacos
→
Tacos with roasted vegetables, beans and salsa
```

---

## 🪶 Lighten It

Ask Forkcast to produce a lower-calorie interpretation.

Example:

```text
Yakiniku + rice
→
Yakiniku + cabbage salad + vegetables
```

This is an obvious future local-AI capability.

---

## 🃏 Wild Card

Introduce a Meal Card that was not in the player's original selection.

The new proposal receives:

**0 Voting Points**

It must gain genuine support to succeed.

---

## 🔁 Second Chance

Return an eliminated proposal to active negotiation.

It does not restore spent Voting Points automatically.

---

## 🎲 Double or Nothing

May be played immediately after Roulette.

Spin again.

The second result becomes binding.

No third attempt.

Civilisation has limits.

---

## 🕊 Peace Treaty

Two players agree to stop actively downvoting one another's nominated meals for the remainder of the session.

Optional cooperative bonus may be tested later.

Keep behaviour simple in v1.

---

# 19. Removed / postponed cards

These ideas should not initially be implemented:

### Chef's Choice

Removed because its functionality overlaps too heavily with I'll Cook.

The chef should naturally have some control over recipe details.

### Call in a Favour

Good future mechanic, but introduces another layer of persistent social debt.

Postpone until the simpler system has been play-tested.

### Veto

Do not implement.

Expensive downvoting already serves this role.

A free Veto would undermine the Voting Point system.

---

# 20. General Assembly

General Assembly is **not a card**.

Any player may call one when a House Rule blocks a desired outcome.

Example:

```text
HOUSE RULE

Maximum one minced-meat dinner.

Monday already contains beef tacos.

Friday Burgers would violate this rule.

CALL GENERAL ASSEMBLY?
```

The General Assembly asks players to spend Voting Points supporting the exception.

Suggested rule:

**At least 4 total Voting Points must support the motion.**

Possible additional rule to test:

At least **two players** must contribute.

Example:

```text
Allow Friday Burgers?

Johan     +1
Anna      +1
Oscar     +2
Elsa       0

TOTAL      4

MOTION PASSES
```

Spent points are removed from the players' weekly budgets.

There are no negative votes in a General Assembly.

Players either support the exception or do not.

---

# 21. Three levels of rules

Forkcast should distinguish three fundamentally different constraint types.

## Hard Rules

Cannot be overridden.

Examples:

- allergies
- medical dietary restrictions
- player physically absent
- ingredient marked unsafe

General Assembly cannot override these.

---

## House Rules

Normal household policies.

Examples:

- at least one fish dinner
- maximum one minced-meat dinner
- at least one vegetarian dinner
- pizza maximum once per week

These can be overridden by General Assembly.

---

## Preferences

Soft optimisation signals.

Examples:

- child had cod at school
- family ate tacos yesterday
- try to eat more vegetables
- avoid very heavy meals several days consecutively
- use food already in refrigerator

Preferences should influence suggestions but never automatically block a meal.

---

# 22. Initial household rules

For the prototype use:

```text
At least 1 fish meal per week.

Maximum 1 minced-meat meal per week.
```

These should be editable household settings.

---

# 23. Chores

The first supported chores should be:

### Chef

One or more people responsible for cooking.

### Cleanup

One or more people responsible for clearing/washing up.

Each dinner entry therefore eventually becomes:

```json
{
  "day": "Thursday",
  "meal": "Yakiniku",
  "chef": ["Johan"],
  "cleanup": ["Oscar"]
}
```

Later:

- chopping/prep
- shopping
- setting table
- leftovers
- packed lunches

can be added.

---

# 24. Game completion

When the week satisfies all non-overridden rules and all days have meals, Forkcast can be locked.

Example final screen:

```text
THE FORKCAST IS IN

MON
🌮 Tacos
Chef: Anna

TUE
🍛 Chicken Curry
Chef: Elsa

WED
🐟 Salmon
Chef: Johan

THU
🥩 Yakiniku
Chef: Johan
Cleanup: Oscar

FRI
🍔 Burgers
General Assembly Exception
```

The week becomes persistent data rather than temporary game state.

---

# 25. Post-game statistics

Optional but desirable.

Examples:

```text
MOST DIPLOMATIC
Anna
4 votes supporting other players

BIGGEST CAMPAIGN
Johan
4 points on Yakiniku

HOUSE HERO
Oscar
2 cleanup duties

POLITICAL LANDSLIDE
Tacos
3 supporters
```

These should be humorous rather than competitive rankings.

Avoid creating long-term leaderboards where family members become incentivised to game domestic chores.

---

# 26. Mobile UX

The mobile experience should use one major interaction per screen.

Avoid dense dashboard layouts.

Typical screens:

```text
Join Forkcast

↓

Choose meals

↓

Place meals on days

↓

Allocate Voting Points

↓

Reveal

↓

Weekly board

↓

Play cards / vote

↓

Resolve rules

↓

Final Forkcast
```

Cards should be large, visual and swipe/tap friendly.

A player should rarely need to type.

---

# 27. Shared game state

All clients subscribe to the current session over WebSockets.

Example messages:

```json
{
  "event": "PLAYER_JOINED",
  "player_id": "johan"
}
```

```json
{
  "event": "MEAL_PLAYED",
  "player_id": "johan",
  "meal_id": "yakiniku",
  "day": "thursday"
}
```

```json
{
  "event": "VOTE_CAST",
  "player_id": "elsa",
  "proposal_id": "proposal_42",
  "points": 1
}
```

```json
{
  "event": "CARD_PLAYED",
  "card": "SWAP"
}
```

The server processes the action and broadcasts the resulting state.

---

# 28. Proposed backend modules

```text
forkcast/
│
├── api/
│   ├── sessions.py
│   ├── players.py
│   ├── meals.py
│   ├── voting.py
│   └── websocket.py
│
├── game/
│   ├── engine.py
│   ├── state_machine.py
│   ├── voting.py
│   ├── cards.py
│   ├── coalitions.py
│   ├── rules.py
│   └── roulette.py
│
├── models/
│   ├── player.py
│   ├── meal.py
│   ├── proposal.py
│   ├── session.py
│   └── household.py
│
├── ai/
│   ├── ollama.py
│   ├── meal_similarity.py
│   ├── recipe_transform.py
│   └── suggestions.py
│
├── database/
│   └── sqlite.py
│
└── main.py
```

Game-engine code should not depend directly on the AI layer.

---

# 29. Suggested frontend structure

```text
src/
│
├── pages/
│   ├── Join.tsx
│   ├── Lobby.tsx
│   ├── MealSelection.tsx
│   ├── Placement.tsx
│   ├── Reveal.tsx
│   ├── GameBoard.tsx
│   └── FinalForkcast.tsx
│
├── components/
│   ├── MealCard.tsx
│   ├── ActionCard.tsx
│   ├── PlayerAvatar.tsx
│   ├── VotingPoints.tsx
│   ├── DayColumn.tsx
│   ├── Proposal.tsx
│   └── RuleAlert.tsx
│
├── game/
│   └── gameTypes.ts
│
├── api/
│   ├── rest.ts
│   └── websocket.ts
│
└── App.tsx
```

---

# 30. Core data model

## Meal

```json
{
  "id": "yakiniku",
  "name": "Yakiniku",
  "emoji": "🥩",
  "tags": [
    "beef",
    "japanese",
    "quick"
  ],
  "protein_type": "beef",
  "minced_meat": false,
  "fish": false
}
```

---

## Proposal

```json
{
  "id": "proposal_123",
  "meal_id": "yakiniku",
  "day": "thursday",
  "owners": [
    "johan"
  ],
  "voting_points": 4,
  "supporters": [
    "johan"
  ],
  "status": "ACTIVE"
}
```

A coalition can simply add owners and supporters.

---

## Player session state

```json
{
  "player_id": "johan",
  "voting_points_remaining": 4,
  "meal_cards": [
    "yakiniku",
    "salmon",
    "tacos"
  ],
  "action_cards": [
    "SWAP",
    "ROULETTE",
    "ILL_COOK"
  ],
  "action_cards_played": []
}
```

---

## Week

```json
{
  "monday": null,
  "tuesday": null,
  "wednesday": null,
  "thursday": null,
  "friday": null
}
```

Once resolved:

```json
{
  "thursday": {
    "meal_id": "yakiniku",
    "chef": [
      "johan"
    ],
    "cleanup": [
      "oscar"
    ],
    "rule_exceptions": []
  }
}
```

---

# 31. REST API outline

Suggested initial endpoints:

```text
POST /api/sessions
GET  /api/sessions/{id}

POST /api/sessions/{id}/join
POST /api/sessions/{id}/start

GET  /api/household
GET  /api/meals
POST /api/meals

POST /api/sessions/{id}/meal-selection
POST /api/sessions/{id}/placement

POST /api/sessions/{id}/vote
POST /api/sessions/{id}/cards/play

POST /api/sessions/{id}/general-assembly

POST /api/sessions/{id}/lock-day
POST /api/sessions/{id}/complete
```

Live state:

```text
WS /ws/sessions/{id}
```

---

# 32. AI capabilities

The home Python server provides an ideal place for optional local AI.

The first implementation could talk to Ollama running on the same machine or another machine on the LAN.

AI should be exposed internally through a simple abstraction.

Example:

```python
class ForkcastAI:
    def suggest_meals(...):
        ...

    def compare_meals(...):
        ...

    def transform_meal(...):
        ...

    def parse_school_menu(...):
        ...
```

---

# 33. Good early AI features

## Meal transformations

Cards such as:

- Spice It Up
- Veg It Up
- Lighten It

can initially call an LLM.

Example input:

```text
Meal: Yakiniku with rice

Transformation:
lower calories

Household preferences:
keep beef
no mushrooms
```

Possible output:

```text
Yakiniku with cabbage salad, cucumber, carrots,
spring onion and reduced rice.
```

---

# 34. Meal coalition AI

Later the AI can evaluate:

```text
Yakiniku

Teriyaki Chicken
```

and return:

```json
{
  "compatible": true,
  "suggestion": "Japanese Bowl Night",
  "reason": "Both are Japanese-style sweet-savory meals"
}
```

The AI suggestion must still be accepted by the players.

---

# 35. School-menu integration

This should be designed for, but does not need to be implemented in the first playable prototype.

Future flow:

```text
School menu
      ↓
Import/API/scraper/manual text
      ↓
AI parses meals
      ↓
Forkcast generates preferences
```

Example:

```text
Wednesday:
School lunch = cod

Preference:
Reduce likelihood of fish dinner Wednesday
```

This remains a soft preference.

The system must not conclude:

```text
FISH ILLEGAL
```

simply because somebody encountered cod at noon.

---

# 36. History

Forkcast should eventually maintain meal history:

```text
2026-08-03  Tacos
2026-08-04  Salmon
2026-08-05  Pasta
```

This allows:

- “we had this recently”
- meal diversity
- favourite statistics
- frequency rules
- AI suggestions

History is useful but not required for the first multiplayer game test.

---

# 37. Future kitchen screen

The backend architecture should assume that a shared display will later join as another client.

Possible URL:

```text
http://forkcast.local/display
```

The shared screen does not need player controls.

It can display:

```text
TONIGHT

🥩 YAKINUKI

Chef
Johan

Cleanup
Oscar

Dinner forecast
18:30
```

Below that:

```text
Tomorrow
🐟 Salmon

Wednesday
🌮 Tacos
```

During planning sessions it could become the shared game board while everyone uses phones as controllers.

This should be considered Phase 2 rather than part of the first prototype.

---

# 38. Development phases

## Phase 1 — Playable skeleton

Implement:

- React mobile client
- Python FastAPI backend
- session creation
- player joining
- avatars
- WebSockets
- five-day board
- Meal Cards
- hidden meal selection
- placement
- reveal
- Voting Points
- final week

No AI.

No sophisticated cards.

Goal:

Four phones can successfully plan a week together.

---

## Phase 2 — Game mechanics

Add:

- Roulette
- Swap
- I'll Cook
- I'll Clean
- Coalition
- General Assembly
- House Rules

Goal:

Determine whether Forkcast is genuinely fun.

---

## Phase 3 — Full first deck

Add:

- Spice It Up
- Veg It Up
- Lighten It
- Wild Card
- Second Chance
- Double or Nothing
- Peace Treaty

Add animations and improved reveal moments.

---

## Phase 4 — Local AI

Add Ollama integration for:

- transformations
- compromise dishes
- meal suggestions
- classification
- recipe generation

---

## Phase 5 — Household intelligence

Add:

- meal history
- school menus
- calendar awareness
- leftovers
- ingredients at home
- nutritional preferences

---

## Phase 6 — Forkcast Display

Create shared kitchen/tablet mode.

Eventually:

```text
Phones = controllers

Kitchen display = game board

Python server = referee + memory + AI
```

---

# 39. First prototype success criteria

The first version is successful if four people can sit together with their phones and:

1. Join the same Forkcast session.
2. Secretly choose meals.
3. Place them onto days.
4. Reveal everybody's choices simultaneously.
5. Spend Voting Points.
6. See proposals move up and down.
7. Assign one meal to each evening.
8. Leave with a saved weekly dinner plan.

If that interaction is enjoyable, cards and AI should be added.

If that interaction is not enjoyable, adding a local language model with seventeen billion parameters will not rescue it.

---

# 40. Product direction

Forkcast should ultimately become two things at once:

### The Sunday game

A short multiplayer family ritual for deciding the coming week's dinners.

### The household dinner interface

The persistent system showing:

- what is for dinner
- who cooks
- who cleans
- what is coming tomorrow
- recipes and variations
- the history of what the household eats

The same backend and data model should power both experiences.

The first engineering goal should therefore be:

> **Build the smallest possible multiplayer Forkcast session that we can actually play as a family on four phones.**