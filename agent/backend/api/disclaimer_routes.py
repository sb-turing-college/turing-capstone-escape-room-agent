"""Disclaimer acceptance endpoints (clickwrap)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from disclaimer_acceptance import (
    DISCLAIMER_FILE,
    accept_disclaimer,
    is_disclaimer_accepted,
)

router = APIRouter(prefix="/agent/disclaimer", tags=["agent"])


@router.get("/status")
def disclaimer_status() -> dict[str, bool]:
    return {"accepted": is_disclaimer_accepted()}


@router.post("/accept")
def disclaimer_accept() -> dict[str, bool]:
    accept_disclaimer()
    return {"accepted": True}


@router.get("/doc")
def disclaimer_doc() -> FileResponse:
    if not DISCLAIMER_FILE.is_file():
        raise HTTPException(status_code=404, detail="DISCLAIMER.md not found.")
    return FileResponse(
        DISCLAIMER_FILE,
        media_type="text/plain; charset=utf-8",
        content_disposition_type="inline",
        filename="DISCLAIMER.md",
    )
