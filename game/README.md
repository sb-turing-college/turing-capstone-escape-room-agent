# The Haunted Manor

Browser-based text adventure (**Chapter 0**) with three rooms, fixed puzzles, and a pixel-art UI. **Escape Room Agent** in [`agent/`](../agent/) plays the same game via the REST API — without access to source code.

> Part of the **turing-capstone-project** monorepo. **Full stack setup, prerequisites, and evaluation:** [root README](../README.md). Capstone case mapping: [ARCHITECTURE.md](../ARCHITECTURE.md).

## Current status

| Area | Status |
|------|--------|
| Game engine + REST API | Implemented — `backend/game/*`, `/game/*` |
| Frontend (human play) | Implemented — start screen, save/load, transitions, demo ending |
| AI agent + dashboard | Implemented — [`agent/`](../agent/) |

**Rooms:** The Library → The Parlor → Lord's Office (`lords_office`)

**Demo goal:** Complete Chapter 0 from the library through the cinematic demo ending.

> **No spoilers here.** Solution chain for tests/dev: `backend/solution_chain.py` (pytest: `tests/test_solution_walkthrough.py`).

## Quick start

From the monorepo root (recommended): `..\scripts\start-game.ps1` (game only) or `..\scripts\start-all.ps1` (with agent). See [../README.md](../README.md).

### Manual (this folder only)

**Backend** (`game/backend`):

```powershell
cd backend
uv sync
uv run uvicorn main:app --reload --port 8000
```

Health: http://localhost:8000/health · API docs: http://localhost:8000/docs

**Frontend** (`game/frontend`):

```powershell
cd frontend
npm install
npm run dev
```

Game: http://localhost:5173 — Vite proxies `/api` → `localhost:8000`.

**Tests:**

```powershell
cd backend
uv run pytest
```

Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)

## Playing

1. Start backend and frontend (scripts or manual above)
2. **Explore** on the start screen (intro → Chapter 0 title → library)
3. Verb buttons, hotspots, or typed commands (e.g. `take brass key`, `look around`, `read memo`). No **Look around** button — use the keyboard.
4. **Save memory** / **Remember** / **Flee** (top right, 3 save slots per browser)

**Layout:** Wide screens (`lg+`) fit one viewport; smaller screens scroll. See [ARCHITECTURE.md](../ARCHITECTURE.md) §2.4.1.

Verbs and fallback messages: `shared/game_constants.json` (`commands` block). Details: [shared/README.md](shared/README.md).

### Spectator mode (Escape Room Agent)

```
http://localhost:5173/?spectate=<session_id>
```

`session_id` from `POST /game/new` or an agent run. UI input disabled; state via polling.

### Example commands

| Action | Example |
|--------|---------|
| Look around | `look around` |
| Inventory | `inventory` or `i` |
| Read | `read memo` (after `take`) |
| Safe | `examine safe` / `use safe` → hint; code via `use safe 123456` |

Other verbs: `examine`, `take`, `use`, `open`, `go`, `pull`, `speak`, `touch`.

## With Escape Room Agent

1. Start game backend **and** frontend (port 5173 for live spectate view)
2. `..\scripts\start-all.ps1` from monorepo root — or [agent/README.md](../agent/README.md)
3. Dashboard: http://localhost:5174

## Configuration

`.env.example` → `.env` (game backend):

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLite path (default: `sqlite:///./capstone.db`) |
| `CORS_ORIGINS` | Allowed frontend origins (default: `http://localhost:5173`) |

Saves: SQLite (`saved_games`), no login — `client_id` in `localStorage`.

## License & disclaimer

| Content | License |
|---------|---------|
| Source code | [AGPL-3.0](../LICENSE) |
| Story, pixel art, sounds | [CC BY-NC-ND 4.0](../LICENSE-ASSETS.md) |

See [DISCLAIMER.md](../DISCLAIMER.md).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Ports 8000/5173 in use | `..\scripts\start-game.ps1 -Restart` from monorepo root |
| Frontend shows backend errors | Backend on port 8000 |
| Empty save/load | Same browser/`client_id`; backend DB not deleted |
| Agent cannot reach game | Backend on 8000; check CORS in `.env` |

General monorepo issues: [../README.md](../README.md#troubleshooting).

## Security

- Never commit `.env`
- No user accounts — local SQLite saves only
- Game API for local demo/development, not hardened for public internet
