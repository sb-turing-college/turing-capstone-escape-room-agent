"""Capstone Agent – FastAPI application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.disclaimer_routes import router as disclaimer_router
from api.run_routes import router as agent_router
from api.ws_handler import router as ws_router
from config import get_settings
from db.database import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Capstone Agent",
    description="ReAct explorer agent with live WebSocket dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings["cors_origins"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(disclaimer_router)
app.include_router(agent_router)
app.include_router(ws_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
