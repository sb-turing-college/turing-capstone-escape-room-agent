"""Agent run REST schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    explorer_model: str | None = None
    memory_model: str | None = None
    max_steps: int = Field(default=50, ge=1, le=200)
    max_human_assists: int = Field(default=0, ge=0, le=3)
    inherit_memory_session_id: str | None = None
    hint: str | None = Field(default=None, max_length=2000)


class RunStartResponse(BaseModel):
    run_id: str
    status: str


class RunSummary(BaseModel):
    run_id: str
    session_id: str | None
    started_at: datetime
    finished_at: datetime | None
    success: bool | None
    steps_count: int
    commands_count: int | None = None
    cumulative_commands_count: int | None = None
    explorer_model: str
    memory_model: str
    status: str
    error_message: str | None = None
    continued_from_run_id: str | None = None
    is_fresh_attempt: bool = False
    memory_session_id: str | None = None
    max_steps: int | None = None
    max_human_assists: int = 0
    human_assists_used: int = 0


class StepInfo(BaseModel):
    step_number: int
    type: str
    content: str
    room: str | None
    timestamp: datetime
    extra: dict | None = None


class RunDetail(RunSummary):
    steps: list[StepInfo]


class ChatMessageInfo(BaseModel):
    id: int
    role: str
    content: str
    timestamp: datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)


class HintRequest(BaseModel):
    human_response: str | None = Field(default=None, max_length=2000)
    hint: str | None = Field(default=None, max_length=2000)

    def resolved_response(self) -> str | None:
        if self.human_response is not None:
            return self.human_response
        return self.hint


class PauseStateResponse(BaseModel):
    status: str
    paused: bool


class ChatResponse(BaseModel):
    user_message: ChatMessageInfo
    assistant_message: ChatMessageInfo
    memory_saved: bool = False


class MemoryEntryInfo(BaseModel):
    id: str
    document: str
    source: str | None = None
    run_id: str | None = None
    memory_session_id: str | None = None
    superseded_by: str | None = None


class ClearMemoryRequest(BaseModel):
    memory_session_id: str | None = None


class SpectateSessionResponse(BaseModel):
    session_id: str | None = None
    restored: bool = False
    pending: bool = False


class ContinueRunRequest(BaseModel):
    hint: str | None = Field(default=None, max_length=2000)
    max_steps: int | None = Field(default=None, ge=1, le=200)
    max_human_assists: int | None = Field(default=None, ge=0, le=3)


class RetryRunRequest(BaseModel):
    hint: str | None = Field(default=None, max_length=2000)
    max_steps: int | None = Field(default=None, ge=1, le=200)
    max_human_assists: int | None = Field(default=None, ge=0, le=3)
