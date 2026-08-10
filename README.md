# Forkcast

Forkcast is a mobile-first family dinner planning game based on the v1 specification in `Forkcast.md`.

This first prototype includes:

- React + TypeScript + Vite phone UI
- FastAPI backend with authoritative in-memory game state
- Session creation and joining
- WebSocket session updates
- Meal selection, secret placement, reveal, negotiation voting, day locking, and final week view
- Prototype house-rule status for fish and minced-meat dinners
- Development simulation mode with three random extra players
- Turn-based negotiation with direct cook/clean commitments

## Run Locally

Install dependencies:

```bash
npm install
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

Start the backend:

```bash
npm run backend
```

Start the frontend in another terminal:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

Phones on the same LAN can use the Vite network URL printed by `npm run dev`.

## Simulation Mode

Use **Create Simulation** on the first screen to create a session as yourself plus three simulated players: Anna, Elsa, and Oscar.

During the game, use **Simulate Next** to let simulated players complete the current phase:

- In meal selection, they choose three random favourites.
- In secret placement, they place meals and spend random Voting Points.
- In reveal, the game advances to negotiation.
- In negotiation, the active simulated player takes a visible turn: vote, play a card, possibly lock a day, then pass.
- In final vote, the simulator completes the Forkcast if house rules are satisfied.

## Negotiation Turns and Chores

Negotiation now has a current-player turn order. The active player can vote, commit to cook or clean directly on a proposal, lock a day, and then pass.

Implemented prototype commitments:

- **I'll Cook** toggles the player as chef for a proposal.
- **I'll Clean** toggles the player for cleanup.

For this prototype pass, every player has **I'll Cook** and **I'll Clean** available directly on meal proposals. These commitments do not grant Voting Points; they are already strategically useful because they help lock preferred meals. Wild Card, Roulette, and Swap are held back while the core negotiation loop is refined. A proposal can only be locked when it is leading its day and has both chef and cleanup volunteers.

## Prototype Notes

State is intentionally in memory for now. Restarting the backend clears sessions. SQLite persistence, richer action cards, General Assembly resolution, and AI meal transformations are planned later phases from the specification.
