"""CLI entry point for terminal agent runs."""

from __future__ import annotations

import argparse
import asyncio

from agent.runner import create_run_record, execute_run
from config import get_settings
from db.database import SessionLocal, init_db
from disclaimer_acceptance import ensure_disclaimer_accepted_interactive


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run Haunted Manor explorer agent")
    parser.add_argument("--explorer-model", default=None)
    parser.add_argument("--memory-model", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    args = parser.parse_args()

    settings = get_settings()
    if not settings["openrouter_api_key"]:
        raise SystemExit("OPENROUTER_API_KEY missing in .env")

    ensure_disclaimer_accepted_interactive()

    init_db()
    db = SessionLocal()
    explorer_model = args.explorer_model or str(settings["default_explorer_model"])
    memory_model = args.memory_model or str(settings["default_memory_model"])
    max_steps = args.max_steps or int(settings["default_max_steps"])
    run = create_run_record(db, explorer_model, memory_model, max_steps=max_steps)
    run_id = run.id
    db.close()

    print(f"Starting run {run_id} with model {explorer_model}")
    await execute_run(run_id, explorer_model, memory_model, max_steps)
    print(f"Run {run_id} finished")


if __name__ == "__main__":
    asyncio.run(main())
