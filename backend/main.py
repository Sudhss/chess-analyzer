from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

try:
    from .engine import analyze_pgn, analyze_single_move
    from .sample_pgn import SAMPLE_PGN
except ImportError:
    from engine import analyze_pgn, analyze_single_move
    from sample_pgn import SAMPLE_PGN


app = FastAPI(title="Chess Review Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    pgn: str | None = None


class MoveRequest(BaseModel):
    fen: str
    uci: str


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sample")
def sample() -> dict[str, str]:
    return {"pgn": SAMPLE_PGN}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    return analyze_pgn(request.pgn)


@app.post("/api/analyze-move")
def move(request: MoveRequest) -> dict:
    return analyze_single_move(request.fen, request.uci)
