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
- In negotiation, they cast a few random votes and lock a complete week.
- In final vote, the simulator completes the Forkcast if house rules are satisfied.

## Prototype Notes

State is intentionally in memory for now. Restarting the backend clears sessions. SQLite persistence, richer action cards, General Assembly resolution, and AI meal transformations are planned later phases from the specification.
