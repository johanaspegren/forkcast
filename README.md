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
- Shared family recipe collection, added from a photo or a link, feeding the meal pool
- Asynchronous swipe voting that proposes a week everyone can live with

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

If no game was played for a week, use the dedicated manual editor page:

```text
http://localhost:5173/display/manual
```

Use **Create manual week** and then fill in each day with the dish, cooks, and cleaners. Manual plans are saved on the backend per week.

The tablet view at `/display` stays read-only and does not show edit controls.

When you run Forkcast on Raspberry Pi, manual plans are stored on the Pi and shown on every device that opens the same server URL.

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

Use **Create Simulation** on the first screen to create a session as yourself plus three simulated players: Mamma, Pappa, and Amanda.

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

## Recipe Collection

Open the family recipe collection at:

```text
http://localhost:5173/recipes
```

Anyone on the LAN can add to it two ways:

- **Drop a photo** of a recipe card (or tap **Fotografera** on a phone). The backend sends the
  photo to Claude, which transcribes it into the Forkcast recipe schema and returns a bounding
  box for the plated dish; that box is used to cut a square thumbnail showing just the serving.
- **Paste a link**. Most Swedish recipe sites (ICA, Coop, Arla, …) publish schema.org
  `Recipe` JSON-LD, which is parsed directly — no API key and no AI needed. If a page has no
  structured data, the page text falls back to Claude.

Every recipe is stored as its own JSON blob in `.forkcast-data/recipes/<id>.json`, using the
same schema as `forkcast_recipes.json`. Source images are kept alongside in `images/`, and
thumbnails in `thumbs/`. **Exportera** downloads the whole collection as a single
`forkcast_recipes.json`; dropping such a file back onto the page imports it.

Recipes join the game's meal pool automatically and appear under the **Recept** tab during
meal selection. The protein, fish and minced-meat flags on each recipe drive the existing
house rules, so a recipe-backed dinner counts the same as a built-in one.

### Photo import setup

Photo import needs an Anthropic API key on the server:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
npm run serve
```

Without a key the page says so and link import keeps working. To use a different model:

```bash
export FORKCAST_RECIPE_MODEL=claude-sonnet-5
```

Transcriptions from photos are marked **Granska** (review) until someone in the family opens
the recipe and confirms it — a recipe card photographed at an angle is not always read
perfectly, and the ingredient amounts are editable.

## Veckans svep (swipe voting)

A third way to decide the week, at:

```text
http://localhost:5173/swipe
```

Unlike Classic Draft and Realtime Rush, this one is **asynchronous** — there is no
session and no lobby. Each family member opens the app whenever they like, picks
themselves from the roster, and swipes through a short deck of meal cards:

- **swipe left** — not this week
- **swipe right** — happy to eat this
- **swipe up** — a favourite, *and* an offer to cook it

The three buttons under the card do the same thing, and are the primary path; the
gesture is an enhancement. Preferences are durable, so the next round only asks
about meals you have not seen yet.

When someone taps **Skapa veckans förslag**, Forkcast picks the week. It is worth
being precise about who decides what:

- The **solver** chooses the menu, deterministically. It scores every possible
  week against each member's own swiping history and picks the one that leaves
  the *worst-off* member best off, subject to the house rules. This runs with no
  API key and no internet.
- The **AI** only ever chooses between weeks the solver has already declared
  equally good, and writes the one-line reason under each dish. It returns an
  index into a list of pre-validated weeks, so it cannot introduce a meal or
  break a house rule. With no key configured it is skipped silently and the
  deterministic reasons are used instead.

The family then accepts, swaps a single day, or rerolls the whole week. Nothing
is locked until someone taps **Lås veckan**, which publishes the week so it
appears on the hallway tablet.

Swiping on a Sunday plans the week that is about to start, matching the display.

### Why a dislike is free

The spec prices blocking expensively and rejects a free veto, but swiping left
has to feel free or nobody finishes the deck. Both hold here because a dislike is
a *weight*, never a block: each member is scored against what a random week would
give **them**, so someone who dislikes most of the deck expects a lot of pain
from any week and avoiding their dislikes earns very little. The only way to
score for them is to include something they actually liked. A member who dislikes
everything cannot capture the week.

### Who has swiped

The hallway tablet shows the round's progress and a QR code whenever a week is
still undecided — async planning has no lobby to remind anyone, so the tablet is
the nudge.

### Optional AI

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export FORKCAST_AI_MODEL=claude-opus-5   # optional override
```

## School Menu Context

Forkcast can fetch the Hässleholm Matilda school menu from:

```text
https://menu.matildaplatform.com/meals/week/6752f62a2554115c468f8cb8_forskola-skola
```

The planning screen shows the current week’s school lunches as soft context. It does not block dinner choices yet.

## Prototype Notes

State is intentionally in memory for now. Restarting the backend clears sessions. SQLite persistence, richer action cards, General Assembly resolution, and AI meal transformations are planned later phases from the specification.
