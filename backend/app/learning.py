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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_cpu (
                pattern TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                score INTEGER NOT NULL,
                seen_count INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_brand (
                pattern TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                seen_count INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS learned_gpu (
                pattern TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                score INTEGER NOT NULL,
                seen_count INTEGER NOT NULL,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


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
    if result.get("gpu") and details.get("gpu_score", 0) == 0:
        flags.append("unknown_gpu_score")
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
    gpu_counts: dict[str, dict[str, Any]] = {}

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
        if "unknown_gpu_score" in flags or not parsed.get("gpu"):
            for gpu in _candidate_gpus(text):
                _bump(gpu_counts, gpu, title)
        if parsed.get("gpu") and parsed.get("details", {}).get("gpu_score") == 0:
            _bump(gpu_counts, parsed["gpu"], title)

    return {
        "cpu_candidates": _top(cpu_counts, limit),
        "brand_candidates": _top(brand_counts, limit),
        "storage_snippets": _top(storage_snippets, limit),
        "gpu_candidates": _top(gpu_counts, limit),
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



def _candidate_gpus(text: str) -> list[str]:
    import re

    upper = text.upper()
    patterns = [
        r"\bRTX\s*(?:PRO\s*)?\d{4}(?:\s*SUPER|\s*TI)?\b",
        r"\bGTX\s*\d{4}(?:\s*SUPER|\s*TI)?\b",
        r"\bRX\s*\d{4}(?:\s*XT|\s*XTX)?\b",
        r"\bRADEON\s*\d{3,4}M\b",
        r"\bARC\s*A\d{3,4}\b",
    ]
    found = []
    for pattern in patterns:
        found.extend(re.findall(pattern, upper, re.I))
    return [" ".join(item.upper().split()) for item in found]


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

AUTO_LEARN_INTERVAL_SECONDS = 300
MIN_CPU_OCCURRENCES = 2
MIN_GPU_OCCURRENCES = 2


def auto_learn() -> dict[str, Any]:
    init_db()
    suggestions = get_suggestions(limit=100)
    learned = {"cpu": [], "gpu": [], "brand": []}

    with sqlite3.connect(DB_PATH) as conn:
        for item in suggestions["cpu_candidates"]:
            if item["count"] < MIN_CPU_OCCURRENCES:
                continue
            label = _normalize_cpu_label(item["value"])
            score = _estimate_cpu_score(label)
            if not label or score is None:
                continue
            conn.execute(
                """
                INSERT INTO learned_cpu (pattern, label, score, seen_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(pattern) DO UPDATE SET
                    label = excluded.label,
                    score = excluded.score,
                    seen_count = excluded.seen_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (item["value"].upper(), label, score, item["count"]),
            )
            learned["cpu"].append({"pattern": item["value"], "label": label, "score": score, "count": item["count"]})

        for item in suggestions["gpu_candidates"]:
            if item["count"] < MIN_GPU_OCCURRENCES:
                continue
            label = _normalize_gpu_label(item["value"])
            score = _estimate_gpu_score(label)
            if not label or score is None:
                continue
            conn.execute(
                """
                INSERT INTO learned_gpu (pattern, label, score, seen_count)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(pattern) DO UPDATE SET
                    label = excluded.label,
                    score = excluded.score,
                    seen_count = excluded.seen_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (item["value"].upper(), label, score, item["count"]),
            )
            learned["gpu"].append({"pattern": item["value"], "label": label, "score": score, "count": item["count"]})

        for item in suggestions["brand_candidates"]:
            if item["count"] < 3:
                continue
            brand = item["value"].strip()
            if len(brand) < 3 or any(char.isdigit() for char in brand):
                continue
            conn.execute(
                """
                INSERT INTO learned_brand (pattern, label, seen_count)
                VALUES (?, ?, ?)
                ON CONFLICT(pattern) DO UPDATE SET
                    label = excluded.label,
                    seen_count = excluded.seen_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (brand.upper(), brand, item["count"]),
            )
            learned["brand"].append({"pattern": brand, "label": brand, "count": item["count"]})

    return learned


def apply_learned_rules(parsed: dict[str, Any], text: str) -> dict[str, Any]:
    init_db()
    updated = dict(parsed)
    upper = text.upper()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if not updated.get("cpu"):
            for row in conn.execute("SELECT pattern, label FROM learned_cpu ORDER BY seen_count DESC"):
                if row["pattern"] in upper:
                    updated["cpu"] = row["label"]
                    break
        if not updated.get("gpu"):
            for row in conn.execute("SELECT pattern, label FROM learned_gpu ORDER BY seen_count DESC"):
                if row["pattern"] in upper:
                    updated["gpu"] = row["label"]
                    break
        if not updated.get("brand"):
            for row in conn.execute("SELECT pattern, label FROM learned_brand ORDER BY seen_count DESC"):
                if row["pattern"] in upper:
                    updated["brand"] = row["label"]
                    break

    return updated


def get_learned_cpu_scores() -> dict[str, int]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT label, score FROM learned_cpu").fetchall()
    return {row["label"]: row["score"] for row in rows}


def get_learned_gpu_scores() -> dict[str, int]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT label, score FROM learned_gpu").fetchall()
    return {row["label"]: row["score"] for row in rows}


def get_learned_rules() -> dict[str, Any]:
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cpus = conn.execute("SELECT pattern, label, score, seen_count, updated_at FROM learned_cpu ORDER BY seen_count DESC").fetchall()
        brands = conn.execute("SELECT pattern, label, seen_count, updated_at FROM learned_brand ORDER BY seen_count DESC").fetchall()
        gpus = conn.execute("SELECT pattern, label, score, seen_count, updated_at FROM learned_gpu ORDER BY seen_count DESC").fetchall()
    return {"cpu": [_row_to_dict(row) for row in cpus], "gpu": [_row_to_dict(row) for row in gpus], "brand": [_row_to_dict(row) for row in brands]}


def _normalize_cpu_label(value: str) -> str | None:
    import re

    upper = " ".join(value.upper().replace(".", " ").replace("-", " ").split())
    ryzen = re.search(r"\bRYZEN\s+([3579])\s+((?:\d{4}|H\s*\d{3})[A-Z]{0,2})\b", upper)
    if ryzen:
        return f"Ryzen {ryzen.group(1)} {ryzen.group(2).replace(' ', '')}"
    intel_core = re.search(r"\bI([3579])\s*(\d{4,5}[A-Z]{0,2})\b", upper)
    if intel_core:
        return f"Intel i{intel_core.group(1)}-{intel_core.group(2)}"
    intel_gen = re.search(r"\bI([3579])\s*(\d{1,2})(?:TH)?\s*GEN\b", upper)
    if intel_gen:
        return f"Intel i{intel_gen.group(1)}-{intel_gen.group(2)}th gen"
    intel_n = re.search(r"\bN(\d{3,4})\b", upper)
    if intel_n:
        return f"Intel N{intel_n.group(1)}"
    celeron = re.search(r"\bCELERON\s+([A-Z]?\d{3,5})\b", upper)
    if celeron:
        return f"Intel Celeron {celeron.group(1)}"
    pentium = re.search(r"\bPENTIUM\s+([A-Z]?\d{3,5})\b", upper)
    if pentium:
        return f"Intel Pentium {pentium.group(1)}"
    return None


def _estimate_cpu_score(label: str) -> int | None:
    import re

    if label.startswith("Ryzen"):
        model = re.search(r"(\d{4})", label)
        if not model:
            return None
        number = int(model.group(1))
        if number >= 8700:
            return 95
        if number >= 7700:
            return 90
        if number >= 6800:
            return 86
        if number >= 5800:
            return 79
        if number >= 5500:
            return 66
        return 55
    if label.startswith("Intel i"):
        model = re.search(r"-(\d{4,5})", label)
        if model:
            number = int(model.group(1)[:2]) if len(model.group(1)) >= 5 else int(model.group(1)[0])
            if number >= 13:
                return 82
            if number >= 12:
                return 74
            if number >= 11:
                return 62
            if number >= 10:
                return 48
            if number >= 8:
                return 43
            return 35
        gen = re.search(r"-(\d{1,2})th gen", label)
        if gen:
            generation = int(gen.group(1))
            return 48 if generation >= 10 else 30
    if label.startswith("Intel N"):
        return 30 if label in {"Intel N100", "Intel N150"} else 12
    if "Celeron" in label or "Pentium" in label:
        return 10
    return None


def _normalize_gpu_label(value: str) -> str | None:
    import re

    upper = " ".join(value.upper().replace("-", " ").split())
    rtx = re.search(r"\bRTX\s*(?:PRO\s*)?(\d{4})(?:\s*(SUPER|TI))?\b", upper)
    if rtx:
        suffix = f" {rtx.group(2)}" if rtx.group(2) else ""
        return f"RTX {rtx.group(1)}{suffix}"
    gtx = re.search(r"\bGTX\s*(\d{4})(?:\s*(SUPER|TI))?\b", upper)
    if gtx:
        suffix = f" {gtx.group(2)}" if gtx.group(2) else ""
        return f"GTX {gtx.group(1)}{suffix}"
    rx = re.search(r"\bRX\s*(\d{4})(?:\s*(XT|XTX))?\b", upper)
    if rx:
        suffix = f" {rx.group(2)}" if rx.group(2) else ""
        return f"RX {rx.group(1)}{suffix}"
    arc = re.search(r"\bARC\s*(A\d{3,4})\b", upper)
    if arc:
        return f"Intel Arc {arc.group(1)}"
    radeon = re.search(r"\bRADEON\s*(\d{3,4}M)\b", upper)
    if radeon:
        return f"Radeon {radeon.group(1)}"
    return None


def _estimate_gpu_score(label: str) -> int | None:
    import re

    model = re.search(r"(\d{4})", label)
    if not model:
        return None
    number = int(model.group(1))
    if label.startswith("RTX"):
        generation = number // 1000
        tier = number % 1000
        base = {50: 92, 40: 72, 30: 50, 20: 38, 10: 18}.get(generation * 10, 35)
        if tier >= 900:
            return min(100, base + 18)
        if tier >= 800:
            return min(100, base + 12)
        if tier >= 700:
            return min(100, base + 5)
        if tier <= 600:
            return max(10, base - 8)
        return base
    if label.startswith("GTX"):
        if number >= 1660:
            return 36
        if number >= 1650:
            return 24
        return 16
    if label.startswith("RX"):
        generation = number // 1000
        tier = number % 1000
        base = {7: 58, 6: 45, 5: 25}.get(generation, 35)
        if tier >= 900:
            return min(100, base + 20)
        if tier >= 800:
            return min(100, base + 12)
        if tier >= 700:
            return min(100, base + 5)
        return base
    if "Arc" in label:
        return 55
    return None
