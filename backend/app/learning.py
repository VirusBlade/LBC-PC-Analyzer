from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "learning.sqlite"


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT NOT NULL,
                price TEXT,
                description TEXT,
                parsed_json TEXT NOT NULL,
                score INTEGER,
                verdict TEXT,
                flags TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_created_at ON observations(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_observations_score ON observations(score)")


def record_observation(payload: dict[str, Any], result: dict[str, Any], url: str | None = None) -> dict[str, Any]:
    init_db()
    flags = detect_flags(result)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO observations (url, title, price, description, parsed_json, score, verdict, flags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                url,
                str(payload.get("title") or ""),
                str(payload.get("price") or ""),
                str(payload.get("description") or "")[:4000],
                json.dumps(result, ensure_ascii=False, sort_keys=True),
                result.get("score"),
                result.get("verdict"),
                json.dumps(flags, ensure_ascii=False),
            ),
        )
    return {"stored": True, "flags": flags}


def detect_flags(result: dict[str, Any]) -> list[str]:
    flags = []
    details = result.get("details") or {}

    if not result.get("cpu"):
        flags.append("missing_cpu")
    elif details.get("cpu_score") == 35:
        flags.append("unknown_cpu_score")
    if not result.get("ram_gb"):
        flags.append("missing_ram")
    if not result.get("storage_gb"):
        flags.append("missing_storage")
    if not result.get("brand"):
        flags.append("missing_brand")
    if result.get("score", 100) < 65 and details.get("cpu_score", 0) >= 75:
        flags.append("low_score_good_cpu")

    return flags


def get_stats() -> dict[str, Any]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute("SELECT COUNT(*) AS total FROM observations").fetchone()["total"]
        rows = conn.execute("SELECT flags FROM observations").fetchall()
        flag_counts: dict[str, int] = {}
        for row in rows:
            for flag in json.loads(row["flags"] or "[]"):
                flag_counts[flag] = flag_counts.get(flag, 0) + 1
        recent = conn.execute(
            """
            SELECT title, score, verdict, flags, created_at
            FROM observations
            ORDER BY id DESC
            LIMIT 10
            """
        ).fetchall()

    return {
        "total": total,
        "flags": dict(sorted(flag_counts.items(), key=lambda item: item[1], reverse=True)),
        "recent": [_row_to_dict(row) for row in recent],
    }


def get_examples(flag: str | None = None, limit: int = 30) -> dict[str, Any]:
    init_db()
    limit = max(1, min(limit, 100))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if flag:
            rows = conn.execute(
                """
                SELECT id, url, title, price, score, verdict, flags, parsed_json, created_at
                FROM observations
                WHERE flags LIKE ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (f'%"{flag}"%', limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, url, title, price, score, verdict, flags, parsed_json, created_at
                FROM observations
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

    return {"examples": [_row_to_dict(row) for row in rows]}


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    if "flags" in data:
        data["flags"] = json.loads(data["flags"] or "[]")
    if "parsed_json" in data:
        data["parsed"] = json.loads(data.pop("parsed_json") or "{}")
    return data



def get_suggestions(limit: int = 30) -> dict[str, Any]:
    init_db()
    limit = max(1, min(limit, 100))
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT title, description, parsed_json, flags
            FROM observations
            ORDER BY id DESC
            LIMIT 500
            """
        ).fetchall()

    cpu_counts: dict[str, dict[str, Any]] = {}
    brand_counts: dict[str, dict[str, Any]] = {}
    storage_snippets: dict[str, dict[str, Any]] = {}

    for row in rows:
        title = row["title"] or ""
        description = row["description"] or ""
        text = f"{title} {description}"
        flags = json.loads(row["flags"] or "[]")
        parsed = json.loads(row["parsed_json"] or "{}")

        if "missing_cpu" in flags or "unknown_cpu_score" in flags:
            for cpu in _candidate_cpus(text):
                _bump(cpu_counts, cpu, title)
        if "missing_brand" in flags:
            for brand in _candidate_brands(text):
                _bump(brand_counts, brand, title)
        if "missing_storage" in flags:
            for snippet in _candidate_storage_snippets(text):
                _bump(storage_snippets, snippet, title)
        if parsed.get("cpu") and parsed.get("details", {}).get("cpu_score") == 35:
            _bump(cpu_counts, parsed["cpu"], title)

    return {
        "cpu_candidates": _top(cpu_counts, limit),
        "brand_candidates": _top(brand_counts, limit),
        "storage_snippets": _top(storage_snippets, limit),
        "note": "Ces suggestions sont candidates: valide-les avant de les ajouter a parser.py/scoring.py.",
    }


def _candidate_cpus(text: str) -> list[str]:
    import re

    upper = text.upper()
    patterns = [
        r"\bRYZEN\s+[3579]\s+(?:\d{4}|H\s*\d{3})[A-Z]{0,2}\b",
        r"\bI[3579]\s*[.-]?\s*\d{4,5}[A-Z]{0,2}\b",
        r"\bI[3579]\s*\d{1,2}(?:TH)?\s*GEN\b",
        r"\bN\d{3,4}\b",
        r"\bCELERON\s+[A-Z]?\d{3,5}\b",
        r"\bPENTIUM\s+[A-Z]?\d{3,5}\b",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, upper, re.I))
    return [" ".join(item.split()) for item in found]


def _candidate_brands(text: str) -> list[str]:
    import re

    known_shapes = re.findall(r"\b[A-Z][A-Za-z0-9]{2,}(?:\s+[A-Z][A-Za-z0-9]{1,}){0,2}\b", text)
    stop = {"Prix", "France", "Windows", "Mini PC", "Très bon", "Livraison", "Annonce"}
    return [item.strip() for item in known_shapes if item.strip() not in stop][:8]


def _candidate_storage_snippets(text: str) -> list[str]:
    import re

    snippets = []
    for match in re.finditer(r".{0,28}\b\d+(?:[,.]\d+)?\s*(?:TO|TB|GO|GB)\b.{0,28}", text, re.I):
        snippet = " ".join(match.group(0).split())
        if any(word in snippet.upper() for word in ["SSD", "NVME", "HDD", "DISQUE", "STOCKAGE", "ROM", "EMMC", "SATA", "M.2", "HARD"]):
            snippets.append(snippet)
    return snippets[:6]


def _bump(bucket: dict[str, dict[str, Any]], key: str, title: str) -> None:
    if not key:
        return
    if key not in bucket:
        bucket[key] = {"value": key, "count": 0, "examples": []}
    bucket[key]["count"] += 1
    if title and title not in bucket[key]["examples"] and len(bucket[key]["examples"]) < 3:
        bucket[key]["examples"].append(title)


def _top(bucket: dict[str, dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return sorted(bucket.values(), key=lambda item: item["count"], reverse=True)[:limit]
