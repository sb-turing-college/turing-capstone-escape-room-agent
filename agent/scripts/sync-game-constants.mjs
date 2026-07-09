#!/usr/bin/env node
/**
 * Developer-only sync: copies shared/game_constants.json from game/
 * into agent/. Recruiters never need to run this — the copies are committed.
 *
 * Usage (monorepo): node scripts/sync-game-constants.mjs
 * Override source: GAME_REPO=../other-path node scripts/sync-game-constants.mjs
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const agentRoot = path.resolve(scriptDir, "..");
const gameRoot = path.resolve(
  process.env.GAME_REPO ?? path.join(agentRoot, "..", "game"),
);
const source = path.join(gameRoot, "shared", "game_constants.json");

const destinations = [
  path.join(agentRoot, "backend", "shared", "game_constants.json"),
  path.join(agentRoot, "frontend", "src", "shared", "game_constants.json"),
];

if (!fs.existsSync(source)) {
  console.error(`Source not found: ${source}`);
  console.error(
    "Expected game/ as sibling of agent/, or set GAME_REPO.",
  );
  process.exit(1);
}

const content = fs.readFileSync(source, "utf8");
JSON.parse(content);

for (const dest of destinations) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, content);
  console.log(`Synced → ${path.relative(agentRoot, dest)}`);
}
