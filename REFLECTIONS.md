# Architectural reflections & accepted trade-offs

This document records **known weaknesses** in the codebase and **why they were left as-is**. It complements [ARCHITECTURE.md](ARCHITECTURE.md) and the README files, which describe the **current implementation** only — not project history or design rationale.

For a capstone evaluation, the goal is not a theoretically pure architecture, but a **working, testable system** with **documented trade-offs** where purity would cost more than it buys.

---

## 1. What “good enough” means here

After a focused refactor pass (map graph DRY, puzzle actions in `interactions.py`, store modularisation, `GameRoom` hooks), the project meets these bars:

- Critical duplication that could cause **silent drift bugs** was removed.
- **Action logic** (what happens when the player types a command) lives in declarative content where possible.
- Both frontends use the same **Zustand composition pattern** (thin store + action modules).
- Contract tests protect the game ↔ agent API boundary.

What remains are **known compromises**, documented in the sections below.

---

## 2. Engine: interaction logic vs. rendering logic

### Observation

Puzzle **actions** (`use safe`, `open lockbox`, …) are defined in `game/backend/game/interactions.py`. The engine dispatches verbs and applies matching rules.

However, `GameSession` in `engine.py` still contains **presentation-oriented** code:

- `_object_states()` — maps flags to UI states (`locked` / `unlocked` / `open`) for `door`, `lockbox`, `safe`, `painting`, `grate`.
- `_resolve_note()` — disambiguates the player word “note” between `note_code` and `note_memo` depending on room and inventory.
- `_room_description()` — assembles room text using content hooks (`describe_overrides`, `room_state_replaces` in `objects.py`), but the **assembly loop** stays in the engine.

So the statement “the engine is completely dumb” would be **imprecise**. More accurate:

| Concern | Where it lives | Status |
|---------|----------------|--------|
| **Action logic** (state changes, hints, code locks) | `interactions.py` | ✅ Data-driven |
| **Rendering logic** (descriptions, visible states for UI) | `engine.py` + partial data in `objects.py` / `rooms.py` | ⚠️ Mixed |

### Why we leave it

A fully generic rendering engine would need a **templating or state-mapping layer** for every object the frontend displays (e.g. declarative `ui_state_from_flags` on each object, or a template language for room descriptions). That is a **second mini-engine** — valuable for a multi-chapter commercial adventure, but **over-engineering for a three-room demo**.

Much of the content is already data (`visible_when_flag`, `describe_overrides`, `room_state_replaces`). The remaining hard-coded pieces (`_object_states`, `_resolve_note`) are **small, stable, and covered by tests**.

### If we revisited this later

- Move `_object_states` mappings into `objects.py` (e.g. `ui_state_flags: ("safe_unlocked", "safe_open")`).
- Replace `_resolve_note` with explicit aliases or a generic ambiguity table in `objects.py`.
- Keep `engine.py` as a thin interpreter over those fields.

**Cost:** Medium refactor + test churn. **Benefit:** Cleaner SoC for a larger content team. **ROI for capstone:** Low.

---

## 3. `runner.py`: orchestrator vs. “god class”

### Observation

`agent/backend/agent/runner.py` coordinates DB persistence, memory retrieval, WebSocket events, game session restore, human-in-the-loop pause, and the LangChain invoke loop in one procedural flow.

Static analysis may label this a “god class”. In practice it behaves as a **linear orchestrator**: read state → call LLM → persist → emit event → repeat.

### Why we leave it

Splitting into many small files (`db_loader.py`, `memory_builder.py`, `llm_caller.py`, …) would improve **theoretical** modularity but often **hurts debuggability** — tracing one run would require jumping across modules for a single sequential story.

There is **no duplicated business logic** between those concerns inside `runner.py`; the trade-off is **navigability in one file** vs. many small modules, not DRY violation.

### If we revisited this later

Extract only when a **new feature** forces it (e.g. multiple agent strategies, pluggable memory backends). Split by **stable boundaries**, not by arbitrary module count.

**ROI for capstone:** Negative — high churn, no user-visible gain.

---

## 4. Other accepted trade-offs

### `run_routes.py`

All agent REST routes in one module. Same rationale as `runner.py`: linear, easy to grep, OpenAPI in one place. No DRY problem.

### `sceneConfig.ts` ↔ game engine

Sprite positions and visibility mirror engine object IDs. Unavoidable for a **pixel UI** unless the backend emitted layout coordinates (out of scope). Risk: new objects must be updated in two places. Mitigation: documented in [ARCHITECTURE.md](ARCHITECTURE.md); content set is small and stable.

### Duplicate `GameState` types (game vs. agent frontend)

The Escape Room Agent dashboard uses a **subset** of fields. A shared npm package would add monorepo tooling for minimal gain at this scale.

### `VerbPanel` / `roomTargets.ts` / `game_constants.json`

Slight overlap in USE-target lists. Each serves a different layer (verb UI, room-specific targets, shared labels). Consolidation would couple UI to JSON schema more tightly.

### `explorer_model.split("/").pop()` in four components

Display-only duplication. A one-line helper would be cleaner but has **zero bug risk** and was deprioritised.

### `useAgentSocket.ts`

Combines WebSocket handling with run lifecycle side effects. Acceptable for a single dashboard; would split if a second consumer of live events appeared.

### Human-in-the-loop pause (Give Hint + `ask_human`)

One pause/resume registry serves two initiators (human spectator vs. agent tool). **Give Hint** never counts against the agent’s assist quota; only `ask_human` does. We accept duplicating pause *semantics* in the UI (hint panel vs. question modal) rather than two backend pause systems — see [ARCHITECTURE.md](ARCHITECTURE.md) §3.1.

Human hints and answers are now **first-class step types** (`human_hint`, `human_response`) so post-run **Agent Chat** can distinguish observer input from Chroma `[memory_retrieved]` entries. Continue-run map replay steps are tagged `extra.replayed: true` and filtered from the interview transcript (with a legacy pre-`game_update` heuristic for older runs). **Command grounding** (run-scoped `send_command` index for the selected run) and **memory supersede** (`supersedes` metadata instead of duplicate or deleted Chroma entries) address interview step-count drift and redundant playbook notes without mid-run memory tools — see [ARCHITECTURE.md](ARCHITECTURE.md) §3.1.

### Agent pytest vs. `agent.db`

Route tests previously seeded `RunRecord` rows via `SessionLocal()` into the dev database (`explorer_model = test/model`, displayed as **model** in Escape Room Agent). Fixed with `api_client` + in-memory `dependency_overrides` in `agent/backend/tests/conftest.py`. Cleanup script: `agent/backend/scripts/cleanup_test_runs.py`.

---

## 5. Fixes that removed real failure modes

These changes removed concrete failure modes:

| Issue | Risk if left unfixed | Resolution |
|-------|----------------------|------------|
| Map graph built in two places (agent) | Live map and replay diverge after a change | Single `applyRoomVisited()` in `mapGraph.ts` |
| Safe hints inline in engine **and** in `interactions.py` | Two code paths; easy to update one and forget the other | Hints only in `interactions.py`; flag-aware matching in engine |
| `object_states` leaked off-room puzzle UI state to agent | Agent could see painting/safe state from parlor via JSON observation | `_object_states()` scoped to objects in current room only |
| Monolithic `agentStore` | Hard to navigate; inconsistent with game frontend | Action modules mirroring `gameStore` |
| Monolithic `GameRoom` | UI and behaviour intertwined | Hooks for input, saves, hotspots |
| API route tests writing to `agent.db` | Phantom **model** runs in Escape Room Agent history | `api_client` fixture + in-memory DB in `conftest.py` |
| Interview chat missing human hints | Agent denied observer hints that existed only in ephemeral LLM messages or unpersisted `resume_hint` | Typed `human_hint` / `human_response` steps + lineage transcript + prompt glossary |
| Interview cited wrong command counts / old playbooks | Chat history and stacked `agent_chat` notes outweighed the selected run’s step log | Command grounding index + `supersedes` metadata (explorer skips superseded notes) |
| Review showed wrong `segment/max` (e.g. `12/10`) | Historical runs used global `liveRunMaxSteps` from the form instead of frozen run config | `runs.max_steps` persisted at start; `resolveRunMaxSteps()` in Review/Live headers |
| Legacy runs missing `/budget` in Decision Graph | Rows created before `max_steps` migration | Optional `scripts/backfill_max_steps.py` infers budget from step log |

The guiding rule: **fix what can silently break or contradict itself**; **document what is merely inelegant**.

---

## 6. Summary for the project report

- The codebase **meets capstone scope**: tested, documented, bounded in scope.
- **Separation of concerns is clearest** at the boundaries that matter: content vs. action dispatch, API vs. engine, store vs. UI, game vs. agent.
- **Remaining issues are documented trade-offs** (see §2–4), not silent backlog.
- Further refactoring (rendering templating, runner split, shared TypeScript packages) would be **over-engineering** relative to Chapter 0’s scope and the submission deadline.

When discussing architecture in the report, prefer precise language:

- ✅ “Action logic is data-driven; rendering assembly remains partially imperative in the engine.”
- ❌ “The engine contains no game-specific knowledge.”

Use the precise phrasing above in reports and reviews.
