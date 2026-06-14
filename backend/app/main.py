from __future__ import annotations

from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .parser import parse_listing
from .scoring import score_listing
from .learning import get_examples, get_stats, get_suggestions, init_db, record_observation


app = FastAPI(title="LBC Mini-PC Analyzer", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    title: str = ""
    price: Union[int, float, str, None] = None
    description: str = ""
    url: Union[str, None] = None


class ObserveRequest(BaseModel):
    title: str = ""
    price: Union[int, float, str, None] = None
    description: str = ""
    url: Union[str, None] = None
    result: dict = {}


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    parsed = parse_listing(payload.title, payload.price, payload.description)
    scoring = score_listing(parsed)
    result = {**parsed, **scoring}
    record_observation(payload.dict(), result, payload.url)
    return result


@app.post("/observe")
def observe(payload: ObserveRequest) -> dict:
    return record_observation(payload.dict(), payload.result, payload.url)


@app.get("/learning/stats")
def learning_stats() -> dict:
    return get_stats()


@app.get("/learning/examples")
def learning_examples(flag: Union[str, None] = None, limit: int = 30) -> dict:
    return get_examples(flag=flag, limit=limit)


@app.get("/learning/suggestions")
def learning_suggestions(limit: int = 30) -> dict:
    return get_suggestions(limit=limit)
