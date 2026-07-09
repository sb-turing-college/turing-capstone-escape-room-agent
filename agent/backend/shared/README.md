# Synced from game/

`game_constants.json` is copied from `game/shared/game_constants.json` (labels, map positions, and `commands` vocabulary for agent prompts).

Recruiters: no action needed — this file is committed as-is.

Developers: after editing the source JSON, run from the `agent/` folder:

```bash
node scripts/sync-game-constants.mjs
```

Then commit the updated copies here and in `frontend/src/shared/`.
