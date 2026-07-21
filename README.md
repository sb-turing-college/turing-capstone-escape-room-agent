# Turing Capstone — The Haunted Manor

A browser-based text adventure (**The Haunted Manor**, Chapter 0) plus **Escape Room Agent** — an autonomous AI agent that plays the same game exclusively through its REST API, without access to game source code.

**Problem:** Evaluating LLM agents on games is unreliable when the agent can read puzzle source code or hidden walkthroughs — benchmarks then measure code access, not reasoning over a fixed environment.

**Research goal:** A controlled sandbox to:

1. Compare AI models on **competency**, **efficiency** (commands to reach the ending — including after cross-run learning), and **tool use**
2. Inspect **reasoning and thinking** traces during play
3. Explore **agentic workflows** and **RAG** in a reproducible setup

**Why a custom escape room (built from scratch):**

- **Unpublished puzzles** — the game and its solutions are not published anywhere. Solution strategies cannot come from public walkthroughs or this title's training-data footprint; the benchmark environment stays under the author's control.
- **API-only access** — the agent interacts through a **contract-tested REST API** (`/game/*`). It cannot read game source, puzzle logic, or development solution files during a run.
- **Controlled experiments** — resume from saved state, start fresh attempts, inject human hints, and cap command budgets so agent behaviour can be studied under fixed parameters.

**What was built:** A reproducible sandbox where a LangChain agent must win Chapter 0 using only the public game API, with human play, live observability, memory across runs, and a dashboard for model comparison.

**How it works:** A FastAPI game engine exposes `/game/*` commands and state; a separate agent backend runs a ReAct loop (`send_command`, `get_state`, optional `ask_human`) with ChromaDB retrieval of agent reflections, run summaries, and interview notes; human hints and answers are persisted as typed step records (`human_hint`, `human_response`); post-run **Agent Chat** uses a lineage-aware step transcript (continue-run chains, map-replay filtered) plus a run-scoped per-run command index for grounding; updated playbooks **supersede** older `agent_chat` notes instead of flooding Chroma; the **Escape Room Agent** dashboard streams reasoning, map discovery, human-in-the-loop pause (Give Hint / agent questions), and an optional spectate view of the human UI.

> **Information for Recruiters & Hiring Managers**  
> This monorepo is my capstone project for Turing College. Clone it, run it locally, and explore the implementation.  
> **Visual overview (PDF):** [docs/Escape-Room-Agent-Overview.pdf](docs/Escape-Room-Agent-Overview.pdf) — project walkthrough with screenshots (game, agent UI, example runs).  
> Source code is **AGPL-3.0**; creative assets are **CC BY-NC-ND 4.0** (see [LICENSE-ASSETS.md](LICENSE-ASSETS.md)).

Architecture (incl. design trade-offs): [ARCHITECTURE.md](ARCHITECTURE.md#6-design-decisions--trade-offs)

## What's inside

| Folder | Description | Details |
|--------|-------------|---------|
| [`game/`](game/) | **The Haunted Manor** — text adventure engine, REST API, pixel-art UI | [game/README.md](game/README.md) |
| [`agent/`](agent/) | **Escape Room Agent** — LangChain explorer, memory, dashboard | [agent/README.md](agent/README.md) |

## Evaluation

**Automated (no API key required):**

| Area | Metric |
|------|--------|
| Game backend | 122 pytest tests (engine, puzzles, save/load, API contract, room-scoped object_states) |
| Agent backend | 121 pytest tests (119 run in CI; 2 integration tests skip without game API); runner, routes, memory, interview grounding/supersede, run nudges, command lineage, `max_steps` persistence/backfill, game client contract |
| Agent frontend | 24 Vitest tests (`stepLogUtils`, `mapGraph`, `wheelInput`) |
| Solvability | Canonical **discovery** walkthrough: **26 commands** → demo ending (`test_solution_walkthrough.py`). That path is the first-principles solve used in tests — not the shortest possible route. |

**Live agent runs (requires `OPENROUTER_API_KEY`):** Each run is stored in SQLite with `success`, `steps_count`, `max_steps` (segment budget), and `explorer_model`. Compare models via the **Review** tab or `GET /agent/runs`. Default step cap: **50** (`DEFAULT_MAX_STEPS`). Beyond binary success, **efficiency** on later attempts (fewer commands after memory / interview notes) is part of the evaluation story. Success rates vary by model and prompt — use **Batch runs** (`POST /agent/batch`) for side-by-side comparison rather than a single fixed score.

**Capstone case mapping:** Primary **Case 2** (AI agent for task automation); includes **Case 1** elements (ChromaDB RAG for cross-run memory + structured step retrieval and command grounding for post-run interview), **human-in-the-loop** pause (`Give Hint`, optional `ask_human` with quota 0–3), and **Case 6** topics (API boundary, contract tests, WebSocket observability). Details: [ARCHITECTURE.md](ARCHITECTURE.md).

## Ethical considerations

- **Privacy:** No user accounts; game saves and agent run history stay in local SQLite/ChromaDB on your machine ([ARCHITECTURE.md](ARCHITECTURE.md#8-ethics-and-limits) §8).
- **Fairness:** Fixed puzzle world; the agent has no access to game source or `solution_chain.py` during play.
- **Safety:** Optional Mistral moderation on outbound commands; API keys only in server-side `.env`.
- **Cost & transparency:** LLM calls use OpenRouter (paid per token); see [DISCLAIMER.md](DISCLAIMER.md) and [agent/README.md](agent/README.md).

Bias from model choice and prompts is possible; runs are logged for manual review in Escape Room Agent.

## Prerequisites

- Python 3.11+ with [uv](https://docs.astral.sh/uv/)
- Node.js 18+
- **Full stack only:** `OPENROUTER_API_KEY` in `agent/.env` (copy from `agent/.env.example`)

## First-time setup (clone or zip)

This repository ships **source only**. Not included (see `.gitignore`):

- Python virtualenvs (`.venv/`) — created on first `uv sync` or `uv run`
- Node dependencies (`node_modules/`) — `npm install` in each `frontend/` folder
- Local data (`*.db`, `chroma_db/`, `agent/.disclaimer_accepted`)

**Easiest:** from the repo root, run `.\scripts\start-game.ps1` (game only) or `.\scripts\start-all.ps1` (full stack). Both scripts install missing deps on first launch; backends use `uv run`.

**Manual (all four parts):**

```powershell
cd game/backend && uv sync
cd ../frontend && npm install
cd ../../agent/backend && uv sync
cd ../frontend && npm install
```

After cloning, open **Escape Room Agent** (http://localhost:5174) once and accept the disclaimer modal before starting LLM runs (or set `DISCLAIMER_ACCEPTED=1` in `agent/.env` for CI/automation).

## Quick start

### Play the game only (no API keys)

Best if you have two minutes and just want to try the adventure.

**Windows:**

```powershell
.\scripts\start-game.ps1
```

Restart: `.\scripts\start-game.ps1 -Restart` · Stop: close the backend/frontend terminal windows

**Linux / macOS:**

```bash
chmod +x scripts/start-game.sh
./scripts/start-game.sh
```

Game: http://localhost:5173 · API docs: http://localhost:8000/docs

### Full stack (The Haunted Manor + Escape Room Agent)

Starts game backend & frontend, Escape Room Agent backend & UI (four terminals).

**Windows:**

```powershell
copy agent\.env.example agent\.env   # set OPENROUTER_API_KEY
.\scripts\start-all.ps1
```

Options: `-SkipGame` · `-NoBrowser`

**Linux / macOS:**

```bash
cp agent/.env.example agent/.env
chmod +x scripts/start-all.sh
./scripts/start-all.sh
```

Options: `--skip-game` · `--no-browser`

| Service | Port |
|---------|------|
| Game backend | 8000 |
| Game frontend | 5173 |
| Agent backend | 8001 |
| Escape Room Agent | 5174 |

Game: http://localhost:5173 · Escape Room Agent: http://localhost:5174

### Using Escape Room Agent (dashboard tabs)

| Tab | Purpose |
|-----|---------|
| **Sessions** | **Run Control** (**Create Session** always first — configure run, command chart) + **Session List** below |
| **Live** | Spectate game, reasoning graph, **Give Hint** / agent questions |
| **Review** | **Agent Chat**, **Agent Memory**, and **Agent Logs** panel (step timeline — not a separate dashboard tab) |

Typical flow: **Create Session** (Run Control) → configure & **Start Run** → watch **Live** → open **Review** after the run ends (run stays selected; tab is not forced away from Live).

## Tests

```powershell
cd game/backend && uv run pytest
cd agent/backend && uv run pytest
cd agent/frontend && npm run test && npm run build
cd game/frontend && npm run build
```

## License & disclaimer

| Content | Location |
|---------|----------|
| Source code (AGPL-3.0) | [LICENSE](LICENSE) |
| Creative assets (CC BY-NC-ND) | [LICENSE-ASSETS.md](LICENSE-ASSETS.md) |
| Disclaimer | [DISCLAIMER.md](DISCLAIMER.md) |
| Architecture & trade-offs | [ARCHITECTURE.md](ARCHITECTURE.md#6-design-decisions--trade-offs) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Ports in use | `.\scripts\start-game.ps1 -Restart` or close terminal windows from `start-all` |
| Agent cannot reach game | Game backend on 8000; check `GAME_API_BASE_URL` in `agent/.env` |
| Live game view empty | Game **frontend** must run on 5173 (included in `start-all`) |
| Missing API key | Copy `agent/.env.example` → `agent/.env`, set `OPENROUTER_API_KEY` |
