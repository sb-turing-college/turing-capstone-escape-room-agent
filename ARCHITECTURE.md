# The Haunted Manor — Architecture

Implementation reference for the **Haunted Manor monorepo** (game engine, human UI, and AI agent). For the **research goal** and motivation, see [README.md](./README.md) (top). For setup and commands, see the same file. Design trade-offs: [§6](#6-design-decisions--trade-offs). Project walkthrough with screenshots: [docs/Escape-Room-Agent-Overview.pdf](docs/Escape-Room-Agent-Overview.pdf).

---

## 1. Monorepo overview

Two components share one adventure world. **The Haunted Manor** (game) owns rules and state; **Escape Room Agent** plays through the contract-tested REST API only — no access to game source code or dev solution files during a run.

```
┌─────────────────────────────────────────────────────────────────┐
│  The Haunted Manor                 Escape Room Agent            │
│  game/frontend (:5173)             agent/frontend (:5174)         │
└───────────────┬──────────────────────────────┬──────────────────┘
                │ REST /api proxy              │ REST + WebSocket
                ▼                              ▼
┌───────────────────────────┐    ┌──────────────────────────────┐
│  game/backend (:8000)     │◄───│  agent/backend (:8001)       │
│  Engine + /game/* API     │    │  LangChain runner, memory,   │
│  SQLite (saves)           │    │  run history, live events    │
└───────────────────────────┘    └──────────────────────────────┘
                ▲                              │
                │  HTTP only (GameClient)      │ ChromaDB + SQLite
                └──────────────────────────────┘
```

| Service | Port | Path |
|---------|------|------|
| Game backend | 8000 | `game/backend/` |
| Game frontend | 5173 | `game/frontend/` |
| Agent backend | 8001 | `agent/backend/` |
| Escape Room Agent | 5174 | `agent/frontend/` |

**Full stack:** `scripts/start-all.ps1` / `scripts/start-all.sh` from the monorepo root. **Game only:** `scripts/start-game.ps1` / `scripts/start-game.sh`.

**Shared data:** `game/shared/game_constants.json` — room/item labels, map positions, and a `commands` block (`verbs`, `syntax_patterns`, `default_fallback` messages). The game backend loads verbs and parser copy from here; agent prompts and tools use the synced copy. Committed copies in `agent/backend/shared/` and `agent/frontend/src/shared/`; sync via `agent/scripts/sync-game-constants.mjs` when labels or command vocabulary change.

**Chapter 0 rooms:** `library` → `parlor` → `lords_office`

**Authoritative IDs and copy:** engine content modules, `game/frontend/src/components/sceneConfig.ts`, and `game_constants.json` — not this document.

---

## 2. Game component

| Area | Location | Notes |
|------|----------|--------|
| Engine | `game/backend/game/` | `verbs.py` (from `game_constants.json`), `objects.py`, `rooms.py`, `interactions.py`; `content.py` re-exports |
| REST API | `game/backend/api/game_routes.py` | `/game/*`, save/load, export/restore |
| Persistence | `game/backend/db/` | SQLite; `SavedGameRecord` |
| Frontend | `game/frontend/src/` | React + Zustand (`gameStore` + action modules); UI hooks under `hooks/` |
| Pixel assets | `game/frontend/public/assets/` | Room backgrounds, sprites, UI (CC BY-NC-ND — see [LICENSE-ASSETS.md](LICENSE-ASSETS.md)) |
| Tests | `game/backend/tests/` | Engine, API contract, save/load, walkthrough |
| Solution (dev) | `game/backend/solution_chain.py` | Canonical discovery walkthrough (26 commands); **spoilers** |

### 2.1 Repository layout

```
game/
├── backend/
│   ├── main.py
│   ├── game/                Engine + content
│   ├── api/game_routes.py
│   └── db/
├── frontend/
│   ├── src/store/           gameStore + action modules
│   ├── src/hooks/           useCommandInput, useSaveSlotsMenu, useHotspotCommand, …
│   ├── src/components/      GameRoom, VerbPanel, sceneConfig, …
│   └── public/assets/       Pixel art (committed PNGs)
└── shared/game_constants.json
```

### 2.2 Engine design

- **Separation:** `GameState` / flags in `state.py`; room graph and objects in `rooms.py` / `objects.py`; verb grammar in `parser.py`; puzzle rules (including hints and code locks) in `interactions.py`.
- **Session:** `GameSession` in `engine.py` parses commands, matches interactions, and returns a stable JSON-shaped response (contract-tested for the agent).
- **Interaction matching:** Rules are selected by verb, object set, room, and code-lock shape. Rules with a satisfied `needs_flags_false` precondition are skipped so multiple rules can share the same verb/object pair (e.g. locked vs unlocked safe).
- **Content changes:** Add or adjust data in `interactions.py` / `rooms.py` / `objects.py` — avoid puzzle logic in the engine loop.
- **Save/load:** Full state via `GameState.to_dict()` / `from_dict()`; three slots per `client_id` in SQLite; export/restore endpoints for agent spectate recovery.

### 2.3 Game REST API

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/game/new` | New session |
| `POST` | `/game/{id}/action` | Execute command |
| `GET` | `/game/{id}/state` | Current state |
| `POST` | `/game/{id}/reset` | Reset session (tests) |
| `GET` | `/game/{id}/export-state` | Raw state dict (agent) |
| `POST` | `/game/restore` | New session from exported state |
| `GET` | `/game/saves` | List slots for `client_id` |
| `POST` | `/game/{id}/save/{slot}` | Save to slot 1–3 |
| `POST` | `/game/{id}/load/{slot}` | Load slot |
| `GET` | `/health` | Liveness |

OpenAPI: http://localhost:8000/docs

### 2.4 Game frontend

- **Views:** `start` → intro / game / load / remember flows via `gameStore` + `AppView`.
- **Store:** `gameStore.ts` composes action modules (`gameApiActions`, `introActions`, `spectatorActions`, …).
- **Game UI:** `GameRoom.tsx` — layout shell; `compactLayout = !isSpectator` toggles desktop viewport-fit vs spectator document flow (§2.4.1). Hooks: command input, save slots, hotspot commands.
- **Scene rendering:** `RoomScene.tsx` + `sceneConfig.ts` (sprite placements, `%`-positioned hotspots, visibility from engine state). Desktop standalone uses CSS container queries for a stable 3:2 box (§2.4.1).
- **Input:** `VerbPanel.tsx` (verb buttons; no **Look around** button — typed only) + typed commands; targets from `roomTargets.ts` + `game_constants.json` extras. The typed command line uses a custom block caret (`.command-block-caret`) shown only while the input is focused (`:focus-within`).
- **Game log:** `TextOutput.tsx` — `compact` prop shortens the panel on standalone desktop (`lg:h-36`). Internal scroll; auto-scrolls to the latest entry **only when the user was already at the bottom** (room descriptions stay visible at the top on entry). When content overflows, a visible scrollbar (`.scrollbar-thin`) and a **Scroll** badge on the **Game Log** header row indicate more text below.
- **Motion:** `framer-motion` for intro, transitions, examine modal.
- **Spectator:** `?spectate=<session_id>` — read-only polling when embedded from Escape Room Agent.

#### 2.4.1 Standalone viewport layout (human play, port 5173)

Standalone play (`compactLayout = !isSpectator` in `GameRoom.tsx`) fills one screen on desktop without page scroll. Mobile keeps natural vertical flow. Spectator mode (`?spectate=`) uses the wider document-flow layout (no `compactLayout`, no `100dvh` lock).

| Breakpoint | Behaviour |
|------------|-----------|
| **Below `lg` (< 1024px)** | Natural vertical document flow; page scroll allowed (`min-height: 100dvh`, no global `overflow: hidden`). Sidebar panels stack without being clipped. `RoomScene` is width-driven: `w-full aspect-[3/2]`. |
| **`lg` and above** | Strict viewport fit: `html` / `body` / `#root` locked to `100dvh` with `overflow: hidden`. Scene + log + sidebar share one screen; sidebar scrolls internally when needed. |

**Design goals**

- Scene, log, and sidebar stay usable on short laptop viewports without clipping.
- No layout thrashing on routine UI updates (game log, hover, caret) — responsive sizing is CSS-only.
- Browser zoom scales the UI uniformly (no `transform: scale()` wrapper, no mixed `vh` + JS scaling).
- `RoomScene` keeps a **stable 3:2 box** so `%`-positioned hotspots stay aligned with the background (`object-cover`).

**Principle:** Standalone play is a **web-app shell** (Flex/Grid + `min-h-0`), not a letterboxed game canvas. Sizing uses native CSS — including [container queries](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_containment/Container_queries) for the scene — not JavaScript measurement.

**Files:** `index.css` (`.game-play-shell`, `.game-room-shell`, `.game-scene-slot`, `.game-scene-fit`), `GameRoom.tsx`, `RoomScene.tsx` (`fitViewport`), `TextOutput.tsx` (`compact`).

| Area | Implementation |
|------|----------------|
| **App wrapper** | `.game-play-shell` in `App.tsx` — flex column; on `lg+`: `flex: 1; min-height: 0; overflow: hidden`. |
| **Game room** | `.game-room-shell` on `GameRoom` root — `max-w-6xl`, flex column, `gap-2`; on `lg+`: `h-full; min-height: 0; flex: 1`. |
| **Main grid** | `lg:grid-cols-[2fr_1fr]`, `lg:flex-1 lg:min-h-0 lg:overflow-hidden`. Left column: `lg:h-full lg:min-h-0`. Aside: `lg:min-h-0`, inner scroll area `lg:flex-1 lg:overflow-y-auto`. |
| **Scene slot** | `.game-scene-slot` wraps `RoomScene` when `compactLayout`. On `lg+`: `container-type: size`, `flex: 1; min-height: 0`, flex-centred. Below `lg`: `width: 100%` only (document flow). |
| **Scene box** | `.game-scene-fit` when `fitViewport` (same as `compactLayout`). On `lg+`: `width: min(100cqw, 100cqh × 3/2)`, `aspect-ratio: 3/2` — fills the slot without distorting. Below `lg`: Tailwind `w-full aspect-[3/2]` (container rule inactive). |
| **TextOutput** | `shrink-0`; `compact` → `lg:h-36` (9 rem). No `vh` units. Log scroll stays inside the panel. |
| **Sidebar** | Slightly smaller type when `compactLayout`; panels scroll inside the aside on `lg+`. |

**Why container queries for the scene?** `RoomScene` children (background, sprites, hotspots) are absolutely positioned — the root div has **no intrinsic size**. `w-auto` / `h-auto` therefore collapses to a tiny box. The slot establishes a sized container; `.game-scene-fit` derives width from whichever constraint binds first (column width or available height), then `aspect-ratio` sets height.

**Layout tree (desktop, `lg+`)**

```
.game-play-shell          App.tsx — 100dvh, overflow hidden
└── .game-room-shell      GameRoom — flex-1, min-h-0, max-w-6xl
    ├── header             shrink-0
    └── grid               flex-1, min-h-0, 2fr | 1fr
        ├── left col       flex col, h-full, min-h-0
        │   ├── .game-scene-slot   flex-1, min-h-0, container-type: size
        │   │   └── .game-scene-fit   RoomScene (3:2, min(cqw, cqh×3/2))
        │   └── TextOutput           shrink-0, lg:h-36
        └── aside          min-h-0, internal scroll
```

Every flex child that should shrink **must** have `min-h-0` (or `min-w-0` in rows). Page scroll on `body` is forbidden on `lg+` standalone play; overflow belongs in `TextOutput` and the sidebar only.

**Props (standalone vs spectator)**

| Prop | Component | When `true` (`!isSpectator`) |
|------|-----------|------------------------------|
| `compactLayout` | `GameRoom` (internal) | Viewport-fit shell, tighter gaps/type |
| `fitViewport` | `RoomScene` | `.game-scene-fit` + slot wrapper |
| `compact` | `TextOutput` | Shorter log panel on desktop |

**Not used:** JavaScript viewport scaling (`useStandaloneViewportScale` removed July 2026). A fixed 1920×1080 letterbox canvas was rejected — it wastes space on ultrawide/portrait; flex distribution suits this UI better.

### 2.5 Assets

Pixel art (room backgrounds, sprites, UI) is **committed** under `game/frontend/public/assets/`. The Vite dev server and production build serve these as static files. Creative assets are licensed under CC BY-NC-ND 4.0 — see [LICENSE-ASSETS.md](LICENSE-ASSETS.md).

---

## 3. Agent component

| Area | Location | Notes |
|------|----------|--------|
| Explorer | `agent/backend/agent/explorer.py` | LangChain ReAct; tools `send_command`, `get_state`, optional `ask_human` |
| Runner | `agent/backend/agent/runner.py` | Run loop, DB persistence, WebSocket events |
| Run nudges | `agent/backend/agent/run_nudges.py` | Continue-start budget, per-round status, fresh-attempt / low-budget hints |
| Command lineage | `agent/backend/agent/run_commands.py` | Segment vs cumulative `send_command` totals; `runs.max_steps` per segment budget |
| Human input | `agent/backend/agent/human_interaction.py` | Typed `human_hint` / `human_response` step persistence |
| Interview | `agent/backend/agent/interview.py`, `interview_context.py` | Post-run chat; lineage transcript; command grounding; `save_to_memory` + supersede; context compression |
| Game client | `agent/backend/agent/game_client.py` | HTTP client to game API; response validation |
| Memory | `agent/backend/memory/chroma_store.py`, `agent/memory_agent.py`, `agent/run_memory.py`, `agent/memory_sources.py` | ChromaDB; run-end docs from in-game reflection or LLM fallback + ground-truth footer; canonical `source` keys with legacy dual-read |
| REST + WS | `agent/backend/api/` | `run_routes.py`, `ws_handler.py` |
| Timestamps | `agent/backend/db/datetime_utils.py` | `utc_now()` — naive UTC via `datetime.now(UTC)` (Python 3.13–safe; SQLite `DateTime` compatible) |
| Dashboard | `agent/frontend/src/` | React; **Sessions** / **Live** / **Review** tabs |
| Tests | `agent/backend/tests/` | Runner, routes, game client contract |

### 3.1 Agent backend flow

1. `POST /agent/run` creates a run record (optional `max_human_assists`: 0–3, `max_steps` segment budget) and starts `execute_run` in the background. The resolved `max_steps` is **frozen on `RunRecord`** at creation (same pattern as `max_human_assists`).
2. The runner creates a game session via `POST /game/new` (or restores exported state for continue/spectate).
3. Each step: memory context → LangChain ReAct → `send_command` / `get_state` / (optional) `ask_human` → persist step → publish WebSocket event.
4. **Human-in-the-loop pause** (shared `run_registry.py` + `await_human_pause_resolution()`):
   - **Give Hint** (human initiator): spectator pauses before the next game action; optional `human_response` on resume. Always available; no assist quota.
   - **ask_human** (agent initiator): when `max_human_assists > 0`, the agent may call `ask_human(current_theory, question)`; run pauses until the spectator responds (text optional). Counts against the run quota only — not Give Hint.
   - **Typed step persistence:** Non-empty human text is stored as dedicated steps via `human_interaction.py`:
     - `human_hint` — Give Hint on resume, Continue/New-Attempt `resume_hint`, or human-initiated pause.
     - `human_response` — spectator answer to `ask_human`.
     - Raw observer text only (no wrapper strings); `extra` may include `initiator` (`human` | `agent`) or `source: resume_hint`.
     - Legacy `system` lines (`▶ Resumed with human hint: …`) remain for the live timeline; interview grounding prefers the typed steps.
5. Stop and other lifecycle events are handled without exposing game internals.
6. On run end, `memory_agent.py` builds the Chroma document via `run_memory.py`: last substantive agent `thought` (≥80 chars) when available (`source: in_game_reflection`), otherwise an LLM summary (`source: fallback_summary`); both append a factual ground-truth footer (room, inventory, commands used, ending). Post-run **Agent Chat** notes are stored separately (`source: agent_chat`).

#### Memory entry `source` metadata (Expand & Contract)

ChromaDB attaches opaque metadata to each stored document. There is **no schema migration layer** (unlike SQLite + Alembic): renaming a metadata field does not update existing vectors on disk. Local `chroma_db/` folders may therefore still contain entries written under older key names.

We use **Expand & Contract** so renames stay safe without rewriting the whole vector store:

| Phase | Behaviour |
|-------|-----------|
| **Expand (write)** | All new persistence uses **canonical** keys only (`memory_agent.py`). |
| **Dual-read (read)** | Retrieval, API responses, and live step extras accept **legacy or canonical** keys and map to canonical at the boundary (`normalize_memory_source()` / `is_agent_chat_source()`). |
| **Contract (future)** | Optional later step: migrate or drop legacy aliases once every environment has been recreated — not required for the capstone. |

**Why not migrate Chroma in place?** A one-off rewrite would touch every document, re-embed or at least re-upsert metadata, and add failure modes for little gain in a local dev capstone. Dual-read keeps old folders working while new runs emit consistent metadata.

| Legacy key (old Chroma writes) | Canonical key (new writes + API/UI) | Meaning |
|--------------------------------|-------------------------------------|---------|
| `interview` | `agent_chat` | Instruction saved from post-run Agent Chat (`save_to_memory`) |
| `agent_reflection` | `in_game_reflection` | Last substantive agent `thought` at run end (preferred over LLM summary) |
| `run_summary` | `fallback_summary` | LLM-generated run summary when no usable reflection exists |

**Order in explorer context and Review UI:** all memory entries are **chronological (oldest first)** — agent-chat instructions first, then up to two most recent run summaries (also oldest-first among those). Later entries override earlier ones on conflict; the explorer prompt states this explicitly. `memory_agent.get_context()` treats both legacy `interview` and canonical `agent_chat` as the same class via `is_agent_chat_source()`. `ChromaStore.list_entries()` sorts by `metadata.created_at` (not document id).

**Supersede (not delete):** When post-run **Agent Chat** saves an updated playbook, `save_to_memory` may pass `supersedes: [doc_id, …]` for older `agent_chat` notes in the same `memory_session_id`. `ChromaStore.mark_superseded()` sets `metadata.superseded_by` on the replaced entry (metadata update only — no vector delete, no Chroma rewrite). `memory_agent.get_context()` **skips** superseded notes so the explorer does not see obsolete routes. `GET /agent/memory` still returns all entries and includes `superseded_by` so Review can show which notes were replaced. Mid-run memory writes and `query_memory` tools were deliberately **not** added (capstone scope).

**Code map (single source of truth → boundaries):**

| Layer | File | Role |
|-------|------|------|
| Constants + mapping | `agent/backend/agent/memory_sources.py` | Canonical keys, legacy aliases, `normalize_memory_source()`, `is_agent_chat_source()` |
| Write | `agent/backend/agent/memory_agent.py` | Persists canonical `source` to Chroma; `store_interview_note` + `supersede_interview_notes` |
| Supersede | `agent/backend/memory/chroma_store.py` | `get_entry`, `mark_superseded` (metadata-only update) |
| Read (run events) | `agent/backend/agent/runner.py` | Normalizes `memory_source` in step `extra` for WebSocket + DB (`memory_retrieved` / `memory_stored`) |
| Read (REST) | `agent/backend/api/run_routes.py` | `GET /agent/memory` returns normalized `source` and optional `superseded_by` |
| UI labels | `agent/frontend/src/lib/memorySourceLabels.ts` | Same mapping; display strings are **not** stored in Chroma (`agent chat`, `in-game reflection`, `fallback summary`) |

Tests: `agent/backend/tests/test_memory_sources.py` (mapping), `test_memory_context.py` (legacy fixtures + supersede filtering), `test_run_summary.py` / `test_interview_memory.py` (canonical write keys, proactive save prompt, supersede flow), `test_interview_grounding.py` (command index), `test_human_interaction_steps.py`, `test_interview_transcript.py`, `test_interview_context.py`, `test_run_nudges.py`, `test_run_commands.py`, `test_runner.py` / `test_run_routes.py` (`max_steps` persistence).

#### Post-run interview transcript (lineage + replay filter)

`GET/POST /agent/run/{id}/chat` builds context from stored steps, not live introspection.

| Concern | Implementation |
|---------|----------------|
| **Lineage span** | **Transcript:** `transcript_lineage_run_ids` / `build_transcript` — current **physical playthrough** only (stops at `is_fresh_attempt`; prior lessons via Chroma `[memory_retrieved]`). **Chat history:** `chat_lineage_run_ids` — all runs sharing `memory_session_id` (Q&A persists across New Attempts and continues). Section headers: `(continued from …)` or `(new attempt from …)`. |
| **Map replay noise** | On **Continue Run**, `replay_map_events_from_steps()` re-emits parent `room_visited` / `item_discovered` steps. New replays carry `extra.replayed: true`. Transcript filter drops pre-`game_update` map steps on **continued** runs only (`is_fresh_attempt` skips that filter). |
| **Prompt glossary** | `INTERVIEW_SYSTEM_PROMPT` maps step types — especially `[human_hint]` / `[human_response]` vs `[memory_retrieved]` (Chroma recall, not the human observer). |
| **Proactive memory** | `save_to_memory` tool: prompt prioritizes **proactive** saves when the human corrects a misconception or reveals puzzle mechanics in chat — same turn, without an explicit “remember this”. When updating a playbook, pass obsolete doc ids in `supersedes` (see memory supersede above). Guardrail: no vague praise / filler. Tool description mirrors the prompt. |
| **Command grounding** | `extract_send_commands` + `format_command_index` inject a **run-scoped ordered `send_command` list for the selected run only** into `INTERVIEW_SYSTEM_PROMPT`. The model must use this index (and matching transcript lines) for step/command counts — not prior chat turns, memory notes, or parent-run anecdotes. |
| **Memory index in prompt** | `format_memory_index` lists active (non-superseded) `agent_chat` doc ids + preview so the model can target `supersedes` when saving replacements. |
| **Chat history** | Prior Q&A across the **memory session** (`memory_session_id`) is passed as messages; older turns may be compressed via `maybe_compress_interview_history`. |

Code: `agent/backend/agent/interview.py` (`build_transcript`, `filter_steps_for_transcript`, `extract_send_commands`, `format_command_index`, `format_memory_index`), `agent/backend/agent/interview_context.py`, `agent/backend/agent/run_state_diff.py` (`replayed` metadata on replay emit).

**Next TODO — interview transcript budget:** `build_transcript` currently embeds the **full** step log for every run in the lineage on **each** `POST /chat` call (~20k+ tokens after several continue/retry attempts). Chat turns are compressed when nearing the model window (`maybe_compress_interview_history`), but the transcript is not. Planned: truncate or summarize older run sections (or cap transcript tokens) before `ask_about_run`, with `z-ai/glm-5.2` and other models registered in `MODEL_CONTEXT_LIMITS`; surface a clear API/UI error when context still overflows.

#### Run limits: `max_steps` vs `max_rounds`

The runner enforces **two independent budgets** (`agent/backend/agent/runner.py`):

| Limit | Meaning | Typical stop condition |
|-------|---------|------------------------|
| **`max_steps`** | Budget for **`send_command`** calls (real game actions). Surfaced in prompts, tools, and the dashboard command counter. | **Primary** — loop breaks when `command_count >= max_steps`. |
| **`max_rounds`** | Upper bound on **outer LLM loop iterations** (one model invocation ≈ one round). Set as `max(12, max_steps + 20)`. | **Safety net** — loop breaks when rounds are exhausted before the command budget is used up. |

**Why `max_steps + 20`?** Some models return to the outer loop after almost every single tool call (≈ one `send_command` per round). That worst case needs at least `max_steps` rounds. Additional rounds happen **without** a successful command: `get_state` only, `ask_human` pauses, moderation blocks, stuck-recovery nudges, text-only replies, or `send_command` rejected at the limit (tool error, no game API call). The **+20 buffer** covers that overhead so a run is not cut off while commands remain — it is **not** extra game-command budget.

**Why `max(12, …)`?** Ensures a sensible minimum round ceiling when `max_steps` is very small.

**What actually bounds progress:** `max_steps`. `max_rounds` prevents an infinite loop if the model keeps spinning in non-command rounds. LangGraph’s inner `recursion_limit` (`min(max_steps * 2, 150)`) is a separate guard for tool chaining within one round.

**Soft vs hard command limit:** At the budget, `tools.py` rejects further `send_command` calls (JSON error, count unchanged). The runner’s `command_count >= max_steps` check is the hard stop before starting another LLM round.

#### Continue Run vs New Attempt

Both **Resume** and **New Attempt** set `continued_from_run_id` (interview/chat lineage and memory session scope). They differ by game reset and metrics:

| Mode | Endpoint | Game state | `is_fresh_attempt` | Command lineage | Interview step transcript |
|------|----------|------------|----------------------|-----------------|---------------------------|
| **Continue Run** | `POST …/continue` | Restored from parent | `false` | Sums this segment + prior **continue** segments back to last New Attempt | Same chain as command lineage |
| **New Attempt** | `POST …/retry` | Fresh library (`POST /game/new`) | `true` | **Resets** — only this run’s `send_command` count | Parent raw step log **excluded**; prior lessons via Chroma `[memory_retrieved]` |
| **Clean session** | `POST /agent/run` | Fresh | `false` | Single run | Single run |

DB columns on `runs` (SQLite migrate in `db/database.py`): `is_fresh_attempt`, `max_steps` (nullable — legacy runs pre-migration). API fields: `commands_count` (segment), `cumulative_commands_count` (lineage total), `max_steps` (segment budget at start). Code: `agent/run_commands.py`, `api/run_routes.py`, `agent/runner.py` (`create_run_record`).

**Persisted `max_steps` (command budget):** Each Start / Continue / Retry stores the **resolved** segment budget on the new run row (`body.max_steps` or `DEFAULT_MAX_STEPS`). Continue and New Attempt each get their **own** `max_steps` — not inherited from the parent run. The live WebSocket `run_started` event still streams `max_steps` for realtime UI; **Review** and finished-run headers use `GET /agent/runs` / `run.max_steps` via `resolveRunMaxSteps()` in `stepLogUtils.ts` (not the global `liveRunMaxSteps` store). Legacy rows with `max_steps = null` show command count only until backfilled — one-off: `uv run python scripts/backfill_max_steps.py` from `agent/backend/` (optional `--dry-run`; infers from last observation `commands_used + commands_remaining` or budget nudges in the step log).

**Dashboard command display** (`stepLogUtils.ts`, `SessionManager`, `SessionLearningCurve`, `DecisionGraphColumn`):
- Table + chart: **cumulative** total for fair run comparison.
- Continue segments: small `↪` + tooltip (`N total commands (X in this segment, Y in previous runs)`).
- Live budget: Decision Graph header shows **segment/max** only (`6/12`); cumulative total as `· total N` only on continue segments where `total > segment`. Legacy runs without `max_steps`: count only. `whitespace-nowrap` on the counter. Session list + chart still use cumulative totals; continue rows show `↪` tooltip.
- New Attempt rows: no `↪` (fresh playthrough metric).

#### Explorer run nudges (`run_nudges.py`)

Injected `HumanMessage`s so the model sees budget/state without relying on stale tool JSON from a rebuilt history:

| Nudge | When | Purpose |
|-------|------|---------|
| `build_continue_start_nudge` | Once before **first** LLM round on Continue | `commands_used=0/{max_steps}` — fresh segment budget (avoids “0 commands left” confusion from parent transcript) |
| `build_round_continuation_nudge` | After each outer LLM round | `Run status: commands_used=…` + room/inventory/ending reminder |
| `build_fresh_attempt_nudge` | Start of New Attempt | Simulation reset; repeat physical actions |
| `build_low_budget_ask_human_nudge` | Once when budget ≤ ~25% | Prompt `ask_human` before quota exhausted |

Tests: `test_run_nudges.py`, `test_run_commands.py`, `test_run_routes.py` (cumulative + `is_fresh_attempt`).

### 3.2 Escape Room Agent dashboard

```
agent/frontend/src/
├── store/
│   ├── agentStore.ts           Zustand composition root
│   ├── agentStoreTypes.ts
│   └── actions/                run, reasoning, map, memory, analysis
├── lib/mapGraph.ts             Shared live/replay map graph builder
├── hooks/                      useAgentSocket, useDisplayRun, …
└── components/dashboard/       SessionsTab, LiveTab, ReviewTab
                                  RunControlPanel (embeds SessionLearningCurve)
                                  SessionManager, SessionLearningCurve
                                  MemoryInterviewPanel (Agent Chat + Agent Memory)
                                  RunAnalysis (Review — step log timeline)
```

**Tab order:** `Sessions` | `Live` | `Review` (default: **Sessions**).

**UX funnel:** configure & start/resume → observe live → review memory, chat, and step log.

- **Sessions tab** (`SessionsTab`) — two vertical blocks:
  1. **Run Control** panel (`RunControlPanel`) — one bordered card; on large screens an internal split grid (`45fr` / `55fr`):
     - **Left:** run configuration — **Draft** label or selected run id, explorer model (dropdown in draft only), max commands, human assists, optional hint, action buttons. **Create Session** is **always visible** and is always the **first** button (empty state, draft, run selected, and while another run is active). It starts or resets draft mode (`setPendingNewSession`). Other buttons follow: **Start Run** (draft), **Resume Run** / **New Attempt** (existing run selected).
     - **Right:** **Command Counter** — SVG learning curve (`SessionLearningCurve`, `variant="embedded"`; cumulative `send_command` totals; last 20 non-running runs; green = success, orange = stopped, red = failed).
  2. **Session List** (`SessionManager`) — full width below the panel; run table (newest first; completion dates **24h**). Row hover highlights the matching chart point (shared `hoveredRunId` between list and counter).
  - **Empty state:** hint *Select a run below or click "Create Session".* + **Create Session**.
  - **Draft** mode (`pendingNewSession`): **Create Session** (first) + **Start Run** (`POST /agent/run`, clean memory) + model dropdown.
  - **Existing run** selected from the list: **Create Session** (first) + **Resume Run** (`POST …/continue`) or **New Attempt** (`POST …/retry`). The session list is the single selector (no session/attempt dropdowns).
  - **While a run is active** (`isRunning`): Run Control stays visible with a short status message, **Create Session**, and the command chart (panel is not hidden — user can start configuring another session without leaving Sessions).
  - Click any row selects that run for **Review** (`analysisRunId`) **without changing tabs**; Run Control reflects the selection for resume/retry.
  - **Start Run** navigates to **Live** (`onRunStarted`). Run end/failure (WebSocket) selects the finished run for **Review** but does **not** force a tab switch — the spectator can stay on **Live**.
- **Live tab:** Game spectate iframe left (`GameSpectatorPanel`, `VITE_GAME_FRONTEND_URL`, default `http://127.0.0.1:5173`); discovered map + **Decision Graph** (reasoning timeline) right. WebSocket events drive live state. Live command header: `segment/max | Total: cumulative`. **Give Hint** pauses before the next game action; optional response on resume. When the agent calls `ask_human`, an **Agent question** modal shows `current_theory` + question until the spectator resumes (with or without text). Typed steps `human_hint` / `human_response` appear in the step log when text was provided.
- **Review tab:** 50/50 grid on large screens — left column **Agent Chat** (top, ~60%) and **Agent Memory** (bottom, ~40%); right column **Agent Logs** (`RunAnalysis` step timeline, filters incl. system/human steps, replay map via the same `mapGraph.applyRoomVisited` helper as Live). Uses the run selected in Sessions (`analysisRunId`). Post-run chat via `GET/POST /agent/run/{id}/chat` (lineage transcript, command grounding, glossary); memory list via `GET /agent/memory` (includes `superseded_by` when a note was replaced).
- **Layout shell:** `App.tsx` uses `h-dvh flex flex-col overflow-hidden`; all three tabs stay **mounted** (`hidden` when inactive) so Live chat and scroll state survive tab switches; each tab scrolls internally (`min-h-0` + `overflow-y-auto` where needed).
- **Store pattern:** Same composition model as `game/frontend` (thin store + action modules). Notable UI state: `pendingNewSession`, `sessionsTabRequested` (optional navigate to Sessions), `analysisRunId`, `activeMemorySessionId`. Run end does **not** auto-switch tabs.

### 3.3 Agent REST API (port 8001)

OpenAPI: http://localhost:8001/docs

| Endpoint | Purpose |
|----------|---------|
| `POST /agent/run` | Start async run (`max_human_assists`: 0–3, default 0); omit `memory_session_id` for a clean session |
| `POST /agent/run/{id}/continue` | **Resume** — new run with restored game state + rebuilt chat from stored steps; fresh `max_steps` segment; `is_fresh_attempt=false`; body: optional `hint`, `max_steps`, `max_human_assists` |
| `POST /agent/run/{id}/retry` | **New attempt** — fresh game, same `memory_session_id`; `is_fresh_attempt=true`; body: optional `hint`, `max_steps`, `max_human_assists` |
| `POST /agent/stop/{id}` | Stop run |
| `POST /agent/run/{id}/pause` · `/resume` | Pause / resume (`/resume` body: `{ "human_response": "..." }`; legacy `hint` alias). WS `run_paused` includes `initiator`, `agent_theory`, `agent_question` when agent-initiated |
| `GET /agent/runs` · `/agent/run/{id}` | History and step log (`commands_count`, `cumulative_commands_count`, `max_steps`, `is_fresh_attempt`) |
| `GET /agent/run/{id}/spectate-session` | Session for live game iframe |
| `GET/POST /agent/run/{id}/chat` | Post-run interview |
| `GET /agent/memory` | ChromaDB entries (incl. `superseded_by` when set) |
| `WS /ws/{run_id}` | Live events |

---

## 4. Integration boundary

- **Contract:** The agent uses only documented `/game/*` endpoints. Both repos run contract tests (`game/backend/tests/test_api_contract.py`, `agent/backend/tests/test_game_client_contract.py`).
- **No code sharing:** Puzzle logic never ships to the agent; only HTTP JSON and synced `game_constants.json` (labels + command vocabulary).
- **Fair observation:** `object_states` in game API responses lists UI states only for objects in the **current room**, so the agent cannot infer off-room puzzle state (e.g. painting/safe while still in the parlor).
- **Spectate / continue:** Agent stores `session_id` and optional exported state per run; Escape Room Agent embeds the human game UI in read-only mode.
- **Labels:** Room and item display names come from `game/shared/game_constants.json` (synced into `agent/`).

---

## 5. Testing and configuration

### Tests

```powershell
cd game/backend && uv run pytest
cd agent/backend && uv run pytest
cd agent/frontend && npm run test && npm run build
cd game/frontend && npm run build
```

| Area | Count | Scope |
|------|-------|--------|
| Game backend | 122 pytest | Engine, puzzles, save/load, API contract, room-scoped `object_states` |
| Agent backend | 121 pytest | Runner, routes, memory, human hints, interview transcript/grounding/supersede, run nudges, command lineage, `max_steps` persistence/backfill, game client contract; 2 integration tests skip without game API on port 8000 |
| Agent frontend | 24 Vitest | `stepLogUtils` (incl. `formatSegmentCommandBudget`, `resolveRunMaxSteps`), `mapGraph`, `wheelInput` |
| Game frontend | — | Build only in CI (no unit tests); layout/scroll behaviour documented in §2.4.1 and §7 |

CI: `.github/workflows/ci.yml`

Optional verbose walkthrough (spoilers): `game/backend/test_solution.py`

### Test database isolation

Agent pytest **does not write run history to `./agent.db`** during normal test runs:

| Layer | Typical tests | Database | Isolation |
|-------|---------------|----------|-----------|
| **Unit / helper** | `test_runner.py`, `test_interview_context.py`, `test_interview_transcript.py`, `test_interview_grounding.py`, `test_human_interaction_steps.py`, `test_memory_context.py`, … | In-memory SQLite via `db_session` in `conftest.py` | Per test |
| **API smoke / routes** | `test_run_routes.py`, `test_agent_api.py` | In-memory SQLite via `api_client` + FastAPI `dependency_overrides[get_db]` | Per test |
| **Chroma memory** | Route smoke hitting `/agent/memory/*` | Temp dir under `%TEMP%/capstone_agent_pytest/chroma_test` (set in `conftest.py`) | Session temp |
| **Game save/load API** | `test_save_load.py` | Default file DB (`capstone.db`); fixture deletes `SavedGameRecord` rows after each test | Partial cleanup |

**Local dev:** Live runs use `agent/backend/agent.db`. If old pytest pollution rows appear (`explorer_model = test/model`, shown in Escape Room Agent as **model** with 0 commands), run:

```powershell
cd agent/backend
uv run python scripts/cleanup_test_runs.py
```

CI runs on a clean checkout; `agent.db` is not committed.

**Timestamps:** Game save slots and agent run/step/chat times use `db/datetime_utils.utc_now()` in each backend (`datetime.now(UTC).replace(tzinfo=None)`). This replaces deprecated `datetime.utcnow()`, stays compatible with existing naive UTC rows in SQLite, and serializes unchanged over the REST API (`2026-07-03T13:31:22.478371`). No migration required.

### Configuration

Game needs no `.env` for local play (defaults below). Agent requires `agent/.env` (from `agent/.env.example`) for `OPENROUTER_API_KEY`.

| Variable | Component | Default | Purpose |
|----------|-----------|---------|---------|
| `DATABASE_URL` | game | `sqlite:///./capstone.db` | Human save slots (optional override) |
| `CORS_ORIGINS` | game | `http://localhost:5173` | Game frontend origin (optional override) |
| `DATABASE_URL` | agent | `sqlite:///./agent.db` | Run history |
| `CHROMA_PERSIST_DIR` | agent | `./chroma_db` | Vector memory |
| `GAME_API_BASE_URL` | agent | `http://127.0.0.1:8000` | Game API target |
| `CORS_ORIGINS` | agent | `http://localhost:5174` | Dashboard origin |
| `OPENROUTER_API_KEY` | agent | — | Required for LLM runs |

---

## 6. Design decisions & trade-offs

Intentional boundaries — what was chosen, and what was deliberately not built.

| Decision | Choice | Why |
|----------|--------|-----|
| Puzzle **actions** vs. **rendering** | Actions live in `interactions.py` (data-driven). Room text and UI object states still assemble partly in `engine.py`. | A full templating layer would be a second mini-engine; overkill for a three-room demo. Action paths that can silently drift are declarative; remaining presentation helpers are small and tested. |
| Agent **runner** | One linear orchestrator in `runner.py` (persist → LLM → emit → repeat). | Splitting into many tiny modules would not remove duplication; it would make one sequential run harder to trace. Extract when a new strategy or backend forces a real boundary. |
| **Pixel UI** layout | Sprite positions in `sceneConfig.ts`; object IDs aligned with the engine. | Layout belongs in the frontend unless the API ships coordinates (out of scope). Content set is small and stable. |
| **Shared TypeScript types** | Game and agent frontends keep separate `GameState` shapes. | Agent needs a subset only; a shared package adds monorepo tooling for little gain at this scale. |
| **Human-in-the-loop** | One pause/resume path for Give Hint and `ask_human`; hints/answers as typed steps (`human_hint`, `human_response`). | Avoid two pause systems. Typed steps keep post-run interview grounded without mid-run memory tools. |

**Precise framing:** action logic is data-driven; rendering assembly remains partially imperative in the engine — not “the engine has no game-specific knowledge.”

---

## 7. Frontend follow-ups (documented, not yet implemented)

Review notes from a layout/UX pass (July 2026). **No code changes scheduled here** — listed for future maintenance.

### Game frontend

| Item | Location | Note |
|------|----------|------|
| No unit tests | `game/frontend/` | Container-query scene sizing (§2.4.1) and log stick-to-bottom logic are untested (build-only in CI). |

### Agent dashboard

| Item | Location | Note |
|------|----------|------|
| Duplicated panel shells | `RunControlPanel.tsx` | Three early-return branches share nearly the same grid layout; a shared wrapper would reduce drift. |
| Redundant **Create Session** in draft | `RunControlPanel.tsx` | In draft mode, **Create Session** beside **Start Run** resets the same draft; harmless but slightly redundant UX. |

---

## 8. Ethics and limits

**Privacy:** No personal accounts; local SQLite only; API keys stay server-side in the agent backend.

**Fairness:** Fixed puzzle solution; agent is prompt-driven, not trained on player data.

**Safety (agent):** Optional Mistral moderation; game commands validated against allowed verbs; agent has no filesystem access to the game repo.

**Autonomy limits:** Agent may fail without memory or human assistance; `ask_human` is optional and quota-limited. Evaluation focuses on architecture and observability, not guaranteed solvability.
