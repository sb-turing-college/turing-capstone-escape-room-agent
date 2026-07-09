"""Tests for human_hint / human_response step persistence."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from agent.human_interaction import (
    HUMAN_HINT,
    HUMAN_RESPONSE,
    emit_human_interaction_step,
    interaction_type_for_initiator,
)
from db.models import StepRecord


def test_interaction_type_for_initiator():
    assert interaction_type_for_initiator("agent") == HUMAN_RESPONSE
    assert interaction_type_for_initiator("human") == HUMAN_HINT


@pytest.mark.asyncio
async def test_emit_human_interaction_step_persists(db_session):
    publish = AsyncMock()
    counter = [0]
    run_id = "run-human-steps"

    await emit_human_interaction_step(
        db_session,
        run_id,
        publish,
        counter,
        text="  Try the portrait first  ",
        interaction_type=HUMAN_HINT,
        room="lords_office",
        extra={"source": "resume_hint"},
    )

    steps = (
        db_session.query(StepRecord)
        .filter_by(run_id=run_id)
        .order_by(StepRecord.step_number)
        .all()
    )
    assert len(steps) == 1
    assert steps[0].type == HUMAN_HINT
    assert steps[0].content == "Try the portrait first"
    assert steps[0].room == "lords_office"
    assert steps[0].extra == {"source": "resume_hint"}
    assert counter == [1]
    publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_emit_human_interaction_step_skips_blank(db_session):
    publish = AsyncMock()
    counter = [3]

    await emit_human_interaction_step(
        db_session,
        "run-blank",
        publish,
        counter,
        text="   ",
        interaction_type=HUMAN_RESPONSE,
    )

    assert db_session.query(StepRecord).filter_by(run_id="run-blank").count() == 0
    assert counter == [3]
    publish.assert_not_awaited()
