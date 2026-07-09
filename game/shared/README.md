# Shared game constants

Single source of truth for display labels, command vocabulary, and UI metadata used by both repos:

- Room and item labels
- Direction labels
- Map node positions (agent live view)
- Room-specific verb targets (`room_use_extras`)
- **Commands** (`commands` block):
  - `verbs` — allowed verb list (game parser, API `available_verbs`, agent prompts)
  - `syntax_patterns` — example command shapes for the agent
  - `default_fallback` — generic engine messages (e.g. touch/pull/speak when no interaction matches)

**game/** imports this file directly (`game_constants.py`). **agent/** keeps a committed copy — sync with `node scripts/sync-game-constants.mjs` from the `agent/` folder after changes here.
