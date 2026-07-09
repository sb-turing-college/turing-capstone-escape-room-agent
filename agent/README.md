# Escape Room Agent

Autonomous AI agent for **The Haunted Manor**. Plays exclusively through the game REST API — no access to game source code.

> Part of the **turing-capstone-project** monorepo. **Setup, prerequisites, ports, and first-time install:** [root README](../README.md).

## Quick start

From the monorepo root (recommended):

```powershell
copy agent\.env.example agent\.env   # set OPENROUTER_API_KEY
.\scripts\start-all.ps1
```

Options: `-SkipGame` · `-NoBrowser` — see [../README.md](../README.md) for Linux/macOS and game-only start.

### Manual (this folder only)

Requires **game/** backend on **8000** and frontend on **5173** (see [../game/README.md](../game/README.md) or `..\scripts\start-game.ps1`).

**Agent backend** (`agent/backend`):

```powershell
cd backend
copy ..\.env.example .env
uv sync
uv run uvicorn main:app --reload --port 8001
```

**Dashboard** (`agent/frontend`):

```powershell
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:5174 · Health: http://localhost:8001/health

**Terminal run (no UI):**

```powershell
cd backend
uv run python -m agent.runner_cli --max-steps 50
```

## Tests

```powershell
cd backend
uv run pytest
uv run pytest -m integration   # needs game API on 8000

cd ..\frontend
npm run test
npm run build
```

Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)

## Dashboard (Escape Room Agent UI)

Tabs: **Sessions** | **Live** | **Review** (http://localhost:5174).

| Tab | What you do |
|-----|-------------|
| **Sessions** | **Run Control** (**Create Session** always first — configure run, command chart) + **Session List** below |
| **Live** | Watch the agent play; **Give Hint** or answer **ask_human** when paused |
| **Review** | **Agent Chat** and **Agent Memory** (left); **Agent Logs** panel / event timeline (right — panel name, not a top-level tab) |

**Agent Chat (Review tab):** Post-run interview via `GET/POST /agent/run/{id}/chat`. **Step transcript** covers the current physical playthrough only (New Attempt resets — prior runs via Chroma `[memory_retrieved]`). **Chat messages** span the full `memory_session_id` so Q&A persists across New Attempts and continues. **Command grounding:** each chat turn injects a run-scoped ordered `send_command` list for the **selected run**, which reduces step-count drift from chat history or memory. **Memory supersede:** `save_to_memory` accepts optional `supersedes` doc ids to mark older `agent_chat` notes obsolete (metadata-only — no Chroma delete); explorer retrieval skips superseded entries. Proactive `save_to_memory` when the human corrects puzzle understanding.

**Resume** (`POST …/continue`) restores mid-game state and injects a fresh command-budget nudge before the first LLM round. **New Attempt** (`POST …/retry`) starts a fresh library game with the same memory session (`is_fresh_attempt=true`). A clean session uses `POST /agent/run` without `memory_session_id`.

**Command metrics:** API returns `commands_count` (this segment) and `cumulative_commands_count` (continue chain since last New Attempt). Each run also stores `max_steps` (segment budget at start). Dashboard table and learning curve use cumulative totals; continue rows show a `↪` tooltip with segment breakdown. Decision Graph header: `commands 6/12` (segment focus); `· total N` only on continue segments; legacy runs without `max_steps` show count only.

## Human-in-the-loop

Two pause flows share one backend mechanism (`run_registry.py`); the UI branches on `initiator`:

| Initiator | Trigger | UI | Quota |
|-----------|---------|-----|-------|
| **Human** | Live tab **Give Hint** | Optional hint panel before next game action | None (always available) |
| **Agent** | `ask_human` tool | Modal with agent status + question | `max_human_assists` 0–3 (Sessions **Human assists**) |

- **0 assists:** no `ask_human` tool, no prompt mention (default).
- **1–3 assists:** agent may call `ask_human(current_theory, question)`; each successful pause/resume consumes one quota slot.
- Resume body: `{ "human_response": "..." }` (legacy `hint` alias). Empty or omitted response → explicit observation `[Human chose not to respond…]`; no typed step is written.
- **Step log:** Non-empty human text is persisted as typed steps (`human_interaction.py`):
  - `human_hint` — Give Hint, Continue/New-Attempt optional hint (`resume_hint`).
  - `human_response` — answer to `ask_human`.
  - Raw text in `content`; `extra` may include `initiator` or `source: resume_hint`.
- Related steps still logged: `action` (`ask_human: …`), `observation` (formatted tool result), `system` (pause/resume lines).

## API (agent backend, port 8001)

OpenAPI: http://localhost:8001/docs

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Agent backend alive |
| `GET /agent/health/game` | Game API reachability |
| `POST /agent/run` | Start agent run (async); body may include `max_human_assists` (0–3) and optional `memory_session_id` (omit for clean session) |
| `POST /agent/run/{run_id}/continue` | **Resume** — restored game state + chat from stored steps; fresh segment budget; body: optional `hint`, `max_steps` (1–200), `max_human_assists` (0–3) |
| `POST /agent/run/{run_id}/retry` | **New attempt** — fresh game, same memory session (`is_fresh_attempt`); body: optional `hint`, `max_steps`, `max_human_assists` |
| `POST /agent/stop/{run_id}` | Stop run |
| `POST /agent/run/{run_id}/pause` | Request pause (Live tab: **Give Hint** flow) |
| `POST /agent/run/{run_id}/resume` | Resume from pause; optional JSON `{ "human_response": "..." }` |
| `POST /agent/batch` | Batch runs across models |
| `GET /agent/runs` | Run history (`commands_count`, `cumulative_commands_count`, `max_steps`, …) |
| `GET /agent/run/{run_id}` | Run detail incl. steps |
| `GET /agent/run/{run_id}/spectate-session` | Session for live game view |
| `GET/POST /agent/run/{run_id}/chat` | Post-run interview chat (grounded command index + `save_to_memory` / `supersedes`) |
| `GET /agent/memory` | Memory entries (`superseded_by` when a note was replaced) |
| `POST /agent/memory/clear` | Clear ChromaDB |
| `GET /agent/models` | OpenRouter models |
| `WS /ws/{run_id}` | Live events |

## Configuration

`.env.example` → `.env` (in `agent/` root):

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | **Required** for agent runs |
| `GAME_API_BASE_URL` | Game backend (default: `http://127.0.0.1:8000`) |
| `MISTRAL_API_KEY` | Optional: command moderation |
| `DATABASE_URL` | SQLite run history |
| `CHROMA_PERSIST_DIR` | Vector memory directory |

Frontend optional: `frontend/.env.example` → `VITE_GAME_FRONTEND_URL` (spectate iframe, default `http://localhost:5173`)

## Optional room backgrounds

Copy static PNGs from the game for the state panel:

```powershell
mkdir frontend\public\assets\rooms
copy ..\game\frontend\public\assets\rooms\*.png frontend\public\assets\rooms\
```

(Copied assets: **CC BY-NC-ND 4.0** — see [../LICENSE-ASSETS.md](../LICENSE-ASSETS.md).)

## OpenRouter budget

API usage incurs provider costs. Plan a budget for test runs; run batch comparisons only after the default model is stable.

## Game constants

Room/item labels, map metadata, and **command vocabulary** live in **game/** `shared/game_constants.json`. This folder holds a committed copy (`backend/shared/`, `frontend/src/shared/`). After editing the source:

```bash
node scripts/sync-game-constants.mjs
```

Details: [backend/shared/README.md](backend/shared/README.md)

## License & disclaimer

| Content | License |
|---------|---------|
| Source code | [AGPL-3.0](../LICENSE) |
| Creative assets | [CC BY-NC-ND 4.0](../LICENSE-ASSETS.md) |

See [DISCLAIMER.md](../DISCLAIMER.md).

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Agent cannot reach game API | Game backend on 8000; `GAME_API_BASE_URL` in `.env` |
| Live game view empty | Game **frontend** on 5173 (use `scripts/start-all.ps1` from monorepo root) |
| WebSocket drops | Keep agent backend running; check run ID in URL |
| Missing `OPENROUTER_API_KEY` | Copy `.env.example` → `.env` |
| Spurious **model** runs (0 commands) in history | `uv run python scripts/cleanup_test_runs.py` from `backend/` |
| Review shows `commands 6` without `/budget` on old runs | `uv run python scripts/backfill_max_steps.py` (`--dry-run` first) |

General monorepo issues (ports, setup): [../README.md](../README.md#troubleshooting).

## Security

- API keys in `.env` only, never commit
- Mistral moderation is best-effort, not a security guarantee
- Agent only calls the game REST API, not the game filesystem
