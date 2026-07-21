# Disclaimer

**The Haunted Manor** and **Escape Room Agent** (turing-capstone-project) are capstone / portfolio projects developed for Turing College. They are provided for educational and demonstration purposes only.

## No warranty and limitation of liability

This software is provided **“as is”** and **“as available”**, without warranty of any kind, whether express or implied, including but not limited to warranties of merchantability, fitness for a particular purpose, accuracy, or non-infringement.

To the **maximum extent permitted by applicable law**, the authors and copyright holders are not liable for any direct, indirect, incidental, special, consequential, or punitive damages arising from use of this software, including loss of data, loss of profits, service interruption, or costs from third-party API use — even if advised of the possibility of such damages.

Some jurisdictions do not allow certain exclusions or limitations; in those cases, our liability is limited to the greatest extent permitted by law.

Program code is also subject to the warranty disclaimer and limitation of liability in **AGPL-3.0** (see [LICENSE](LICENSE), sections 15–17).

## Not a commercial product

This project is not a finished commercial game or production AI service. Features, content, agent behaviour, models, and APIs may change without notice. Do not use it for critical, legal, medical, financial, or safety-related decisions.

## AI and autonomous agent use

The **Escape Room Agent** uses third-party large language models (LLMs) and acts **autonomously** within the game API. By running it, you acknowledge the following:

- **No guarantee of correctness.** Agent outputs — including commands, reasoning text, run summaries, retrieved memory, and post-run **Agent Chat** replies — may be wrong, incomplete, inconsistent, or inappropriate. They are **not** professional, legal, technical, or other advice.
- **Non-deterministic behaviour.** Results vary by model, prompt, temperature, provider, and randomness. Success rates and command counts are not guaranteed.
- **Autonomous action.** The agent may execute many game commands without per-step human approval. You are responsible for supervising runs, stopping them when needed, and for all consequences of agent actions within your environment.
- **Human-in-the-loop input.** Hints and answers you provide (e.g. **Give Hint**, responses to **ask_human**) may be stored locally and influence later behaviour. You are responsible for what you submit.
- **Memory and retrieval.** Vector memory (ChromaDB) and run history can be incomplete, outdated, or misleading. Do not treat stored agent notes as ground truth.
- **Third-party processing.** Prompts, game state, logs, and chat content may be sent to external providers (e.g. **OpenRouter** and underlying model hosts) under **their** terms and privacy policies. We do not control model behaviour, availability, pricing, or data handling by those providers.
- **Not for unsupervised public deployment.** Running a modified or public-facing instance is at your own risk; you must comply with AGPL-3.0 source-offer obligations and applicable law.

## Spoilers and development secrets

Solution paths, puzzle codes, and walkthrough data (e.g. `game/backend/solution_chain.py`) are intended for **development and testing only**. Do not use them if you want to experience the game without spoilers.

The agent backend includes puzzle hints for moderation and tooling (e.g. `agent/backend/agent/game_secrets.py`). These exist for technical reasons; treat them as development material, not public game content.

## Creative assets

Story text, pixel art, and other creative content in `game/`, as well as the project overview PDF and its screenshots under `docs/`, are licensed separately under **CC BY-NC-ND 4.0** (see [LICENSE-ASSETS.md](LICENSE-ASSETS.md)). You may not use these assets commercially or create derivative works without permission.

Optional room PNGs copied into `agent/frontend/public/assets/rooms/` remain under the same CC license.

## Source code license

Program code is licensed under **AGPL-3.0** (see [LICENSE](LICENSE)). If you modify and run a networked version, you must offer corresponding source to users as required by the license.

## Local data and privacy

The game stores save data in a local SQLite database. The agent stores run history (SQLite) and vector memory (ChromaDB) locally. No account system or cloud sync is provided. You are responsible for securing your own environment, backups, and `.env` files.

## Third-party services and LLM costs

The **Escape Room Agent** in `agent/` uses third-party LLM APIs (e.g. **OpenRouter** by default). API usage may incur costs according to the provider’s pricing, including unexpected usage if keys are exposed or runs are left unattended. Never commit API keys; keep `.env` local and private.

## Moderation

Optional Mistral moderation blocks some suspicious agent commands before they reach the game API. It is **best-effort only**: it does not validate the quality of model outputs, prevent all harmful content, or replace human supervision.
