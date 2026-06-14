from __future__ import annotations

from typing import Any


CPU_TABLE = {
    "Ryzen 7 H255": 98,
    "Ryzen 7 8745HS": 98,
    "Ryzen 7 8700G": 96,
    "Ryzen 7 7735HS": 92,
    "Ryzen 9 6900HX": 91,
    "Ryzen 7 6800U": 88,
    "Ryzen 7 5800H": 84,
    "Ryzen 7 5800U": 79,
    "Intel i5-12400": 82,
    "Intel i5-1250P": 78,
    "Intel i5-1235U": 74,
    "Ryzen 7 5700U": 76,
    "Ryzen 5 5650GE": 72,
    "Ryzen 5 7430U": 70,
    "Ryzen 5 5500U": 66,
    "Ryzen 5 unknown": 55,
    "Ryzen 7 unknown": 65,
    "Ryzen 9 unknown": 75,
    "Intel i5-1135G7": 62,
    "Intel i7-6700HQ": 54,
    "Intel i5-9500": 52,
    "Intel i5-7500": 45,
    "Intel i5-8500T": 43,
    "Intel i3-10th gen": 40,
    "Intel i5-10th gen": 48,
    "Intel i7-10th gen": 56,
    "Intel i5-6500T": 35,
    "Intel i3-7th gen": 24,
    "Intel N150": 34,
    "Intel N100": 30,
    "Intel N4000": 12,
    "Intel G630": 8,
    "AMD A10": 15,
}

TRUSTED_BRANDS = {"Beelink", "Lenovo", "HP", "Shuttle", "Minisforum"}
PENALIZED_CPUS = {"Intel N100", "Intel N150", "Intel N4000", "Intel G630", "AMD A10", "Intel i5-8500T", "Intel i5-6500T", "Intel i3-7th gen"}


def _ram_score(ram_gb: int | None) -> int:
    if not ram_gb:
        return 25
    if ram_gb >= 32:
        return 100
    if ram_gb >= 16:
        return 78
    if ram_gb >= 8:
        return 48
    return 20


def _storage_score(storage_gb: int | None, storage_type: str | None) -> int:
    if not storage_gb:
        return 30
    score = 50
    if storage_gb >= 512:
        score = 86
    if storage_gb >= 1024:
        score = 100
    if storage_type == "HDD":
        score -= 25
    if storage_type == "NVMe":
        score += 5
    return max(0, min(100, score))


def _price_score(price: int | None, cpu_score: int, ram_gb: int | None, storage_gb: int | None) -> int:
    if not price:
        return 45

    target = 120 + cpu_score * 3.1
    if ram_gb and ram_gb >= 32:
        target += 55
    elif ram_gb and ram_gb >= 16:
        target += 25
    if storage_gb and storage_gb >= 1024:
        target += 45
    elif storage_gb and storage_gb >= 512:
        target += 25

    ratio = price / target
    if ratio <= 0.65:
        return 100
    if ratio <= 0.8:
        return 88
    if ratio <= 1:
        return 72
    if ratio <= 1.2:
        return 50
    if ratio <= 1.45:
        return 28
    return 10


def _verdict(score: int) -> str:
    if score >= 82:
        return "Excellent"
    if score >= 65:
        return "Bon"
    if score >= 45:
        return "Moyen"
    return "À éviter"


def score_listing(parsed: dict[str, Any], learned_cpu_scores: dict[str, int] | None = None) -> dict[str, Any]:
    cpu = parsed.get("cpu")
    cpu_scores = {**CPU_TABLE, **(learned_cpu_scores or {})}
    cpu_score = cpu_scores.get(cpu, 35)
    ram_score = _ram_score(parsed.get("ram_gb"))
    storage_score = _storage_score(parsed.get("storage_gb"), parsed.get("storage_type"))
    price_score = _price_score(parsed.get("price"), cpu_score, parsed.get("ram_gb"), parsed.get("storage_gb"))

    score = cpu_score * 0.5 + ram_score * 0.2 + storage_score * 0.1 + price_score * 0.2
    adjustments = []

    if cpu in PENALIZED_CPUS:
        score -= 8
        adjustments.append("CPU peu performant ou ancien")
    if parsed.get("brand") in TRUSTED_BRANDS:
        score += 4
        adjustments.append("marque rassurante")
    if parsed.get("ram_gb") and parsed["ram_gb"] >= 32:
        score += 4
        adjustments.append("32 Go de RAM ou plus")
    if parsed.get("storage_gb") and parsed["storage_gb"] >= 512 and parsed.get("storage_type") in {"SSD", "NVMe"}:
        score += 3
        adjustments.append("SSD confortable")

    final_score = max(0, min(100, round(score)))
    verdict = _verdict(final_score)
    reason = _reason(parsed, verdict, adjustments, price_score)

    return {
        "score": final_score,
        "verdict": verdict,
        "reason": reason,
        "details": {
            "cpu_score": cpu_score,
            "ram_score": ram_score,
            "storage_score": storage_score,
            "price_score": price_score,
            "adjustments": adjustments,
        },
    }


def _reason(parsed: dict[str, Any], verdict: str, adjustments: list[str], price_score: int) -> str:
    cpu = parsed.get("cpu") or "CPU non identifie"
    ram = f"{parsed['ram_gb']} Go RAM" if parsed.get("ram_gb") else "RAM inconnue"
    storage = parsed.get("storage_label") or "stockage inconnu"

    if verdict == "À éviter":
        return f"{cpu}, {ram}, {storage}: rapport prix/performance faible."
    if price_score >= 80:
        return f"{cpu}, {ram}, {storage}: prix attractif pour cette configuration."
    if adjustments:
        return f"{cpu}, {ram}, {storage}: {', '.join(adjustments[:2])}."
    return f"{cpu}, {ram}, {storage}: configuration coherente mais prix a verifier."
