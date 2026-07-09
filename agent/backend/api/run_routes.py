"""REST endpoints for agent runs."""

from __future__ import annotations

from db.datetime_utils import utc_now

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from agent.interview import ask_about_run, build_transcript
from agent.interview_context import load_chat_history, maybe_compress_interview_history
from agent.memory_session import filter_memory_entries, run_ids_for_memory_session
from agent.memory_sources import normalize_memory_source
from agent.run_commands import (
    command_lineage_run_ids_db,
    cumulative_command_count,
    lineage_run_ids_db,
)
from agent.run_registry import (
    cancel_run,
    is_run_paused,
    request_pause,
    submit_human_response_and_resume,
)
from agent.runner import create_run_record, execute_run
from api.schemas.agent import (
    ChatMessageInfo,
    ChatRequest,
    ChatResponse,
    ClearMemoryRequest,
    ContinueRunRequest,
    HintRequest,
    MemoryEntryInfo,
    PauseStateResponse,
    RetryRunRequest,
    RunDetail,
    RunRequest,
    RunStartResponse,
    RunSummary,
    SpectateSessionResponse,
    StepInfo,
)
from config import get_settings
from db.database import get_db
from disclaimer_acceptance import require_disclaimer_accepted
from db.models import ChatMessageRecord, RunRecord, StepRecord
from memory.chroma_store import ChromaStore

router = APIRouter(prefix="/agent", tags=["agent"])


def _is_send_command_action(content: str | None) -> bool:
    return (content or "").strip().lower().startswith("send_command:")


def _resolved_max_steps(requested: int | None, settings: dict) -> int:
    return requested or int(settings["default_max_steps"])


# Cache restored game sessions per run (survives game-backend restarts).
_spectate_session_cache: dict[str, str] = {}


@router.get("/models")
def list_models() -> dict[str, list[str] | str]:
    settings = get_settings()
    return {
        "models": list(settings["available_models"]),
        "default_explorer_model": str(settings["default_explorer_model"]),
        "default_memory_model": str(settings["default_memory_model"]),
    }


@router.post("/run", response_model=RunStartResponse)
def start_run(
    body: RunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_disclaimer_accepted),
) -> RunStartResponse:
    settings = get_settings()
    if not settings["openrouter_api_key"]:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured.")

    explorer_model = body.explorer_model or str(settings["default_explorer_model"])
    memory_model = body.memory_model or str(settings["default_memory_model"])
    max_steps = _resolved_max_steps(body.max_steps, settings)
    run = create_run_record(
        db,
        explorer_model,
        memory_model,
        memory_session_id=body.inherit_memory_session_id,
        max_steps=max_steps,
        max_human_assists=body.max_human_assists,
    )

    background_tasks.add_task(
        execute_run,
        run.id,
        explorer_model,
        memory_model,
        max_steps,
        body.max_human_assists,
        resume_hint=body.hint,
    )
    return RunStartResponse(run_id=run.id, status="running")


@router.post("/run/{run_id}/continue", response_model=RunStartResponse)
def continue_run(
    run_id: str,
    body: ContinueRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_disclaimer_accepted),
) -> RunStartResponse:
    """Starts a NEW run that continues a finished one with a fresh step
    budget (Section: Continue Run). Conversation context is rebuilt from the
    source run's stored steps — see agent.runner._rebuild_messages_from_steps.
    """
    settings = get_settings()
    if not settings["openrouter_api_key"]:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured.")

    source = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Run not found.")
    if source.status == "running":
        raise HTTPException(
            status_code=409, detail="Run is still running — stop it first or wait for it to finish."
        )
    if source.success:
        raise HTTPException(status_code=409, detail="Run already succeeded — nothing to continue.")
    if not source.session_id and not source.game_state_json:
        raise HTTPException(
            status_code=409, detail="No saved game state for this run — cannot continue."
        )

    max_human_assists = (
        body.max_human_assists
        if body.max_human_assists is not None
        else source.max_human_assists
    )
    max_steps = _resolved_max_steps(body.max_steps, settings)
    new_run = create_run_record(
        db,
        source.explorer_model,
        source.memory_model,
        max_steps=max_steps,
        max_human_assists=max_human_assists,
        continued_from_run_id=run_id,
    )
    new_run.memory_session_id = source.memory_session_id or run_id
    db.commit()

    background_tasks.add_task(
        execute_run,
        new_run.id,
        explorer_model=source.explorer_model,
        memory_model=source.memory_model,
        max_steps=max_steps,
        resume_from_run_id=run_id,
        resume_hint=body.hint,
        max_human_assists=max_human_assists,
    )
    return RunStartResponse(run_id=new_run.id, status="running")


@router.post("/run/{run_id}/retry", response_model=RunStartResponse)
def retry_run(
    run_id: str,
    body: RetryRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_disclaimer_accepted),
) -> RunStartResponse:
    """Start a fresh game in the same memory session (new attempt, not mid-game resume)."""
    settings = get_settings()
    if not settings["openrouter_api_key"]:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured.")

    source = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Run not found.")
    if source.status == "running":
        raise HTTPException(
            status_code=409, detail="Run is still running — stop it first or wait for it to finish."
        )

    max_human_assists = (
        body.max_human_assists
        if body.max_human_assists is not None
        else source.max_human_assists
    )
    max_steps = _resolved_max_steps(body.max_steps, settings)
    new_run = create_run_record(
        db,
        source.explorer_model,
        source.memory_model,
        memory_session_id=source.memory_session_id or run_id,
        max_steps=max_steps,
        max_human_assists=max_human_assists,
        continued_from_run_id=run_id,
        is_fresh_attempt=True,
    )
    db.commit()

    background_tasks.add_task(
        execute_run,
        new_run.id,
        explorer_model=source.explorer_model,
        memory_model=source.memory_model,
        max_steps=max_steps,
        max_human_assists=max_human_assists,
        fresh_attempt=True,
        resume_hint=body.hint,
    )
    return RunStartResponse(run_id=new_run.id, status="running")


@router.post("/stop/{run_id}")
def stop_run(run_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status != "running":
        return {"status": run.status}
    if cancel_run(run_id):
        return {"status": "stopping"}
    raise HTTPException(status_code=409, detail="Run is not active in this process.")


@router.post("/run/{run_id}/pause", response_model=PauseStateResponse)
def pause_run(run_id: str, db: Session = Depends(get_db)) -> PauseStateResponse:
    """Human-in-the-loop breakpoint (Section 4): asks the run to pause before
    its next game action (send_command/get_state tool call) — it does NOT
    abort the run, unlike /stop."""
    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status != "running":
        raise HTTPException(status_code=409, detail=f"Run is not running (status={run.status}).")
    if request_pause(run_id, initiator="human"):
        return PauseStateResponse(status="pausing", paused=True)
    if is_run_paused(run_id):
        return PauseStateResponse(status="already_paused", paused=True)
    raise HTTPException(status_code=409, detail="Run is not active in this process.")


@router.post("/run/{run_id}/resume", response_model=PauseStateResponse)
def resume_run(
    run_id: str,
    body: HintRequest,
    db: Session = Depends(get_db),
) -> PauseStateResponse:
    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if submit_human_response_and_resume(run_id, body.resolved_response()):
        return PauseStateResponse(status="resumed", paused=False)
    raise HTTPException(status_code=409, detail="Run is not currently paused.")


@router.get("/runs", response_model=list[RunSummary])
def list_runs(db: Session = Depends(get_db)) -> list[RunSummary]:
    runs = db.query(RunRecord).order_by(RunRecord.started_at.desc()).all()
    action_rows = (
        db.query(StepRecord.run_id, func.count())
        .filter(StepRecord.type == "action")
        .filter(StepRecord.content.like("send_command:%"))
        .group_by(StepRecord.run_id)
        .all()
    )
    command_counts = {run_id: count for run_id, count in action_rows}
    continued_from = {r.id: r.continued_from_run_id for r in runs}
    is_fresh_attempt = {r.id: bool(r.is_fresh_attempt) for r in runs}
    return [
        RunSummary(
            run_id=r.id,
            session_id=r.session_id,
            started_at=r.started_at,
            finished_at=r.finished_at,
            success=r.success,
            steps_count=r.steps_count,
            commands_count=command_counts.get(r.id, 0),
            cumulative_commands_count=cumulative_command_count(
                r.id, command_counts, continued_from, is_fresh_attempt
            ),
            explorer_model=r.explorer_model,
            memory_model=r.memory_model,
            status=r.status,
            error_message=r.error_message,
            continued_from_run_id=r.continued_from_run_id,
            is_fresh_attempt=bool(r.is_fresh_attempt),
            memory_session_id=r.memory_session_id,
            max_steps=r.max_steps,
            max_human_assists=r.max_human_assists,
            human_assists_used=r.human_assists_used,
        )
        for r in runs
    ]


@router.get("/run/{run_id}", response_model=RunDetail)
def get_run(run_id: str, db: Session = Depends(get_db)) -> RunDetail:
    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    steps = (
        db.query(StepRecord)
        .filter_by(run_id=run_id)
        .order_by(StepRecord.step_number)
        .all()
    )
    segment_commands = sum(1 for s in steps if _is_send_command_action(s.content))
    command_lineage_ids = command_lineage_run_ids_db(db, run.id)
    lineage_action_rows = (
        db.query(StepRecord.run_id, func.count())
        .filter(StepRecord.run_id.in_(command_lineage_ids))
        .filter(StepRecord.type == "action")
        .filter(StepRecord.content.like("send_command:%"))
        .group_by(StepRecord.run_id)
        .all()
    )
    lineage_counts = {rid: count for rid, count in lineage_action_rows}
    lineage_runs = db.query(RunRecord).filter(RunRecord.id.in_(command_lineage_ids)).all()
    continued_from = {row.id: row.continued_from_run_id for row in lineage_runs}
    is_fresh_attempt = {row.id: bool(row.is_fresh_attempt) for row in lineage_runs}
    return RunDetail(
        run_id=run.id,
        session_id=run.session_id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        success=run.success,
        steps_count=run.steps_count,
        commands_count=segment_commands,
        cumulative_commands_count=cumulative_command_count(
            run.id, lineage_counts, continued_from, is_fresh_attempt
        ),
        explorer_model=run.explorer_model,
        memory_model=run.memory_model,
        status=run.status,
        error_message=run.error_message,
        continued_from_run_id=run.continued_from_run_id,
        is_fresh_attempt=bool(run.is_fresh_attempt),
        memory_session_id=run.memory_session_id,
        max_steps=run.max_steps,
        max_human_assists=run.max_human_assists,
        human_assists_used=run.human_assists_used,
        steps=[
            StepInfo(
                step_number=s.step_number,
                type=s.type,
                content=s.content,
                room=s.room,
                timestamp=s.timestamp,
                extra=s.extra,
            )
            for s in steps
        ],
    )


@router.get("/run/{run_id}/spectate-session", response_model=SpectateSessionResponse)
async def get_spectate_session(run_id: str, db: Session = Depends(get_db)) -> SpectateSessionResponse:
    from agent.game_client import GameClient

    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")

    if run_id in _spectate_session_cache:
        return SpectateSessionResponse(
            session_id=_spectate_session_cache[run_id],
            restored=True,
        )

    settings = get_settings()
    client = GameClient(str(settings["game_api_base_url"]))
    try:
        if run.session_id or run.game_state_json:
            try:
                state, restored = await client.restore_session(
                    session_id=run.session_id,
                    game_state_json=run.game_state_json,
                )
            except RuntimeError:
                state = None
            else:
                session_id = state["session_id"]
                if restored:
                    _spectate_session_cache[run_id] = session_id
                return SpectateSessionResponse(session_id=session_id, restored=restored)

        if run.status == "running":
            # Background task just started (new_game() HTTP call + DB commit
            # still in flight) — not an error, client should retry shortly.
            return SpectateSessionResponse(pending=True)

        raise HTTPException(
            status_code=404,
            detail="No game state snapshot available for this run.",
        )
    finally:
        await client.close()


@router.get("/run/{run_id}/chat", response_model=list[ChatMessageInfo])
def get_run_chat(run_id: str, db: Session = Depends(get_db)) -> list[ChatMessageInfo]:
    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    messages = load_chat_history(db, run)
    return [
        ChatMessageInfo(
            id=m.id,
            role=m.role,
            content=m.content,
            timestamp=m.timestamp,
        )
        for m in messages
    ]


@router.post("/run/{run_id}/chat", response_model=ChatResponse)
async def post_run_chat(
    run_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_disclaimer_accepted),
) -> ChatResponse:
    settings = get_settings()
    if not settings["openrouter_api_key"]:
        raise HTTPException(status_code=400, detail="OPENROUTER_API_KEY not configured.")

    run = db.query(RunRecord).filter_by(id=run_id).one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found.")
    if run.status == "running":
        raise HTTPException(
            status_code=409,
            detail="Interview chat is only available after the run has finished.",
        )

    history = load_chat_history(db, run)
    transcript = build_transcript(db, run)
    question = body.message.strip()
    history = await maybe_compress_interview_history(
        db,
        run,
        history,
        transcript,
        run.memory_model,
        pending_question=question,
    )
    store = ChromaStore(str(settings["chroma_persist_dir"]))
    reply = await ask_about_run(
        run,
        transcript,
        history,
        question,
        store,
        run.memory_model,
        db,
    )

    user_record = ChatMessageRecord(
        run_id=run_id,
        role="user",
        content=question,
        timestamp=utc_now(),
    )
    assistant_record = ChatMessageRecord(
        run_id=run_id,
        role="assistant",
        content=reply.text,
        timestamp=utc_now(),
    )
    db.add(user_record)
    db.add(assistant_record)
    db.commit()
    db.refresh(user_record)
    db.refresh(assistant_record)

    return ChatResponse(
        user_message=ChatMessageInfo(
            id=user_record.id,
            role=user_record.role,
            content=user_record.content,
            timestamp=user_record.timestamp,
        ),
        assistant_message=ChatMessageInfo(
            id=assistant_record.id,
            role=assistant_record.role,
            content=assistant_record.content,
            timestamp=assistant_record.timestamp,
        ),
        memory_saved=reply.memory_saved,
    )


@router.get("/memory/count")
def memory_count(
    memory_session_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    settings = get_settings()
    store = ChromaStore(str(settings["chroma_persist_dir"]))
    if not memory_session_id:
        return {"count": store.count}
    run_ids = run_ids_for_memory_session(db, memory_session_id)
    entries = filter_memory_entries(store.list_entries(), memory_session_id, run_ids)
    return {"count": len(entries)}


@router.get("/memory", response_model=list[MemoryEntryInfo])
def list_memory(
    memory_session_id: str | None = None,
    db: Session = Depends(get_db),
) -> list[MemoryEntryInfo]:
    settings = get_settings()
    store = ChromaStore(str(settings["chroma_persist_dir"]))
    entries = store.list_entries()
    if memory_session_id:
        run_ids = run_ids_for_memory_session(db, memory_session_id)
        entries = filter_memory_entries(entries, memory_session_id, run_ids)
    return [
        MemoryEntryInfo(
            id=entry["id"],
            document=entry["document"],
            source=normalize_memory_source(
                entry["metadata"].get("source") if entry["metadata"] else None
            ),
            run_id=(entry["metadata"].get("run_id") if entry["metadata"] else None),
            memory_session_id=(
                entry["metadata"].get("memory_session_id") if entry["metadata"] else None
            ),
            superseded_by=(
                entry["metadata"].get("superseded_by") if entry["metadata"] else None
            ),
        )
        for entry in entries
    ]


@router.post("/memory/clear")
def clear_memory(
    body: ClearMemoryRequest | None = None,
    db: Session = Depends(get_db),
) -> dict[str, str | int]:
    """Wipe learned memory (ChromaDB).

    When ``memory_session_id`` is set, only that playthrough's memories are
    removed. Otherwise clears the entire Chroma collection (legacy behaviour).
    """
    settings = get_settings()
    store = ChromaStore(str(settings["chroma_persist_dir"]))
    session_id = body.memory_session_id if body else None
    if session_id:
        run_ids = run_ids_for_memory_session(db, session_id)
        removed = store.clear_session(session_id, run_ids)
        return {"status": "cleared", "removed": removed, "memory_session_id": session_id}
    removed = store.clear()
    return {"status": "cleared", "removed": removed}


@router.get("/health/game")
async def game_health() -> dict[str, bool | str]:
    from agent.game_client import GameClient

    settings = get_settings()
    client = GameClient(str(settings["game_api_base_url"]))
    ok = await client.health_check()
    await client.close()
    return {"game_api_reachable": ok, "game_api_base_url": str(settings["game_api_base_url"])}
