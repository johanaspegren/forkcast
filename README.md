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
- Live hallway menu display with rotating restaurant-inspired styles

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

If your preferred default backend port is busy, Forkcast automatically picks the next free one and prints it in the terminal.

To prefer a different starting port before fallback, set `BACKEND_PORT`:

```bash
BACKEND_PORT=8010 npm run backend
```

Start the frontend in another terminal:

```bash
npm run dev
```

If port 5173 is busy, frontend also automatically picks the next free port.

Frontend reads backend port from the latest backend runtime file automatically. If needed, you can still force proxy target manually:

```bash
BACKEND_PORT=8010 npm run dev
```

Open:

```text
http://localhost:5173
```

Phones on the same LAN can use the Vite network URL printed by `npm run dev`.

## Hallway Menu Display

Open a read-only live menu view on a tablet:

```text
http://localhost:5173/display?session=<session-id>
```

To check the hallway tablet without creating a real session, open the built-in mock week:

```text
http://localhost:5173/display?mock=1
```

On a Raspberry Pi server, use:

```text
http://<raspberry-pi-ip>:<selected-port>/display?session=<session-id>
```

The display updates through the session WebSocket and rotates between Classic Dining, Art Deco, and Burger Shack menu styles.

## Raspberry Pi Home Server

Yes, Forkcast can run on a Raspberry Pi as a LAN server. A Raspberry Pi 4 or 5 is a good target.

Use a current Node.js release that can run Vite 7; Node 20+ is a safe choice.

Install system dependencies:

```bash
sudo apt update
sudo apt install -y git nodejs npm python3 python3-venv
```

Clone or copy the project to the Pi, then install app dependencies:

```bash
cd forkcast-2
npm install
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

Build the phone UI and run the combined server:

```bash
npm run build
npm run serve
```

If your preferred backend port is busy on the Pi, `npm run serve` automatically falls forward to a free one. The frontend dev server does the same for port 5173 when you run `npm run dev`.

To choose the starting preference:

```bash
BACKEND_PORT=8010 npm run serve
```

Open from phones on the same Wi-Fi:

```text
http://<raspberry-pi-ip>:<selected-port>
```

Optional systemd service:

Copy the provided unit file to systemd, then edit `User` and `WorkingDirectory` if your Pi uses different values:

```bash
sudo cp deploy/forkcast.service /etc/systemd/system/forkcast.service
sudo systemctl daemon-reload
sudo systemctl enable --now forkcast.service
sudo systemctl status forkcast.service
```

Then run:

```bash
sudo journalctl -u forkcast.service -f
```

### Update or Restart the Service

After updating the project on the Pi, rebuild the phone UI and restart the running service:

```bash
cd ~/forkcast-2
git pull
npm run build
sudo systemctl restart forkcast.service
sudo systemctl status forkcast.service
```

Use `sudo systemctl daemon-reload` only after changing `deploy/forkcast.service`; `sudo systemctl enable --now forkcast.service` is needed only for the initial setup. To inspect the service after a restart, run `sudo journalctl -u forkcast.service -f`.

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

## School Menu Context

Forkcast can fetch the Hässleholm Matilda school menu from:

```text
https://menu.matildaplatform.com/meals/week/6752f62a2554115c468f8cb8_forskola-skola
```

The planning screen shows the current week’s school lunches as soft context. It does not block dinner choices yet.

## Prototype Notes

State is intentionally in memory for now. Restarting the backend clears sessions. SQLite persistence, richer action cards, General Assembly resolution, and AI meal transformations are planned later phases from the specification.
