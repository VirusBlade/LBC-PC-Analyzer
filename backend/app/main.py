from __future__ import annotations

import threading
import time
from typing import Union

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .parser import parse_listing
from .scoring import score_listing
from .learning import AUTO_LEARN_INTERVAL_SECONDS, apply_learned_rules, auto_learn, get_examples, get_learned_cpu_scores, get_learned_gpu_scores, get_learned_rules, get_stats, get_suggestions, init_db, record_observation


app = FastAPI(title="LBC PC Analyzer", version="0.2.0")

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
    start_auto_learning_worker()


def start_auto_learning_worker() -> None:
    def worker() -> None:
        while True:
            time.sleep(AUTO_LEARN_INTERVAL_SECONDS)
            try:
                auto_learn()
            except Exception:
                pass

    thread = threading.Thread(target=worker, daemon=True, name="lbc-auto-learning")
    thread.start()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    parsed = parse_listing(payload.title, payload.price, payload.description)
    parsed = apply_learned_rules(parsed, f"{payload.title} {payload.description}")
    scoring = score_listing(parsed, learned_cpu_scores=get_learned_cpu_scores(), learned_gpu_scores=get_learned_gpu_scores())
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


@app.post("/learning/auto-run")
def learning_auto_run() -> dict:
    return auto_learn()


@app.get("/learning/rules")
def learning_rules() -> dict:
    return get_learned_rules()
