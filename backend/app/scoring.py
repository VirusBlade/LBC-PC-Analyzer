from __future__ import annotations

from typing import Any

from .benchmarks import cpu_score_from_benchmark, gpu_score_from_benchmark


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
    "Ryzen 7 5700X": 86,
    "Ryzen 5 5650GE": 72,
    "Ryzen 5 7430U": 70,
    "Ryzen 5 5500U": 66,
    "Ryzen 5 unknown": 55,
    "Ryzen 7 unknown": 65,
    "Ryzen 9 unknown": 75,
    "Intel i5-1135G7": 62,
    "Intel i7-6700HQ": 54,
    "Intel i7-4790K": 34,
    "Intel i5-9500": 52,
    "Intel i5-7500": 45,
    "Intel i3-8109U": 38,
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

CPU_RELEASE_YEARS = {
    "Ryzen 7 H255": 2025,
    "Ryzen 7 8745HS": 2024,
    "Ryzen 7 8700G": 2024,
    "Ryzen 7 7735HS": 2023,
    "Ryzen 9 6900HX": 2022,
    "Ryzen 7 6800U": 2022,
    "Ryzen 7 5800H": 2021,
    "Ryzen 7 5800U": 2021,
    "Ryzen 7 5700U": 2021,
    "Ryzen 7 5700X": 2022,
    "Ryzen 5 5650GE": 2021,
    "Ryzen 5 7430U": 2024,
    "Ryzen 5 5500U": 2021,
    "Intel i5-12400": 2022,
    "Intel i5-1250P": 2022,
    "Intel i5-1235U": 2022,
    "Intel i5-1135G7": 2020,
    "Intel i7-6700HQ": 2015,
    "Intel i7-4790K": 2014,
    "Intel i5-9500": 2019,
    "Intel i5-7500": 2017,
    "Intel i3-8109U": 2018,
    "Intel i5-8500T": 2018,
    "Intel i5-6500T": 2015,
    "Intel i3-10th gen": 2020,
    "Intel i5-10th gen": 2020,
    "Intel i7-10th gen": 2020,
    "Intel i3-7th gen": 2017,
    "Intel N150": 2025,
    "Intel N100": 2023,
    "Intel N4000": 2017,
    "Intel G630": 2011,
    "AMD A10": 2012,
}

BRAND_ADJUSTMENTS = {
    "PC Custom": (0, "configuration assemblee"),
    "Lenovo": (5, "marque pro fiable"),
    "HP": (5, "marque pro fiable"),
    "Dell": (5, "marque pro fiable"),
    "Shuttle": (5, "marque pro fiable"),
    "Minisforum": (4, "bonne marque PC compact"),
    "Beelink": (4, "bonne marque PC compact"),
    "GMKtec": (2, "marque PC compact correcte"),
    "Geekom": (3, "bonne marque PC compact"),
    "MSI": (3, "bonne marque PC"),
    "Asus": (3, "bonne marque PC"),
    "Acer": (1, "marque correcte"),
    "Intel": (3, "NUC / plateforme reconnue"),
    "Chuwi": (-2, "marque entree de gamme"),
    "NiPoGi": (-3, "marque a verifier"),
    "Acemagic": (-2, "marque a verifier"),
}
TRUSTED_BRANDS = {brand for brand, (delta, _reason) in BRAND_ADJUSTMENTS.items() if delta >= 4}
PENALIZED_CPUS = {"Intel N100", "Intel N150", "Intel N4000", "Intel G630", "AMD A10", "Intel i7-4790K", "Intel i5-8500T", "Intel i5-6500T", "Intel i3-8109U", "Intel i3-7th gen"}


def cpu_release_year(cpu: str | None, benchmark: dict[str, Any] | None = None) -> int | None:
    if not cpu:
        return None
    if benchmark and benchmark.get("year"):
        return int(benchmark["year"])
    if cpu in CPU_RELEASE_YEARS:
        return CPU_RELEASE_YEARS[cpu]
    if cpu.startswith("Ryzen"):
        return _ryzen_release_year(cpu)
    if cpu.startswith("Intel i"):
        return _intel_release_year(cpu)
    if cpu.startswith("Intel N"):
        return 2025 if cpu == "Intel N150" else 2023 if cpu == "Intel N100" else None
    return None


def _ryzen_release_year(cpu: str) -> int | None:
    import re

    match = re.search(r"\b(\d{4})", cpu)
    if not match:
        return None
    number = int(match.group(1))
    if number >= 8700:
        return 2024
    if number >= 7700:
        return 2023
    if number >= 6800:
        return 2022
    if number >= 5700:
        return 2021
    if number >= 5500:
        return 2021
    if number >= 3700:
        return 2019
    return None


def _intel_release_year(cpu: str) -> int | None:
    import re

    gen_label = re.search(r"-(\d{1,2})th gen", cpu)
    if gen_label:
        generation = int(gen_label.group(1))
    else:
        model = re.search(r"-(\d{4,5})", cpu)
        if not model:
            return None
        raw = model.group(1)
        generation = int(raw[:2]) if len(raw) >= 5 else int(raw[0])

    return {
        14: 2023,
        13: 2022,
        12: 2022,
        11: 2020,
        10: 2020,
        9: 2019,
        8: 2018,
        7: 2017,
        6: 2015,
    }.get(generation)


def _ram_score(ram_gb: int | None, ram_type: str | None = None, ram_speed_mhz: int | None = None) -> int:
    if not ram_gb:
        return 25
    if ram_gb >= 64:
        score = 100
    elif ram_gb >= 32:
        score = 92
    elif ram_gb >= 16:
        score = 76
    elif ram_gb >= 8:
        score = 45
    else:
        score = 20

    if ram_type == "DDR5":
        score += 5
    elif ram_type == "DDR3":
        score -= 8
    if ram_speed_mhz and ram_speed_mhz >= 5600:
        score += 3
    elif ram_speed_mhz and ram_speed_mhz < 2666:
        score -= 5
    return max(0, min(100, score))


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
    if storage_type == "SATA SSD":
        score -= 3
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


def score_listing(parsed: dict[str, Any], learned_cpu_scores: dict[str, int] | None = None, learned_gpu_scores: dict[str, int] | None = None) -> dict[str, Any]:
    cpu = parsed.get("cpu")
    benchmark_score, benchmark = cpu_score_from_benchmark(cpu)
    learned_cpu_scores = learned_cpu_scores or {}
    cpu_scores = {**CPU_TABLE, **learned_cpu_scores}
    if cpu in learned_cpu_scores:
        cpu_score = learned_cpu_scores[cpu]
        cpu_score_source = "learned"
    elif benchmark_score is not None:
        cpu_score = benchmark_score
        cpu_score_source = "benchmark"
    else:
        cpu_score = cpu_scores.get(cpu, 35)
        cpu_score_source = "manual" if cpu in CPU_TABLE else "fallback"
    learned_gpu_scores = learned_gpu_scores or {}
    gpu = parsed.get("gpu")
    gpu_score, gpu_benchmark = gpu_score_from_benchmark(gpu)
    if gpu in learned_gpu_scores:
        gpu_score = learned_gpu_scores[gpu]
        gpu_score_source = "learned"
    elif gpu_score is not None:
        gpu_score_source = "benchmark"
    else:
        gpu_score = 0
        gpu_score_source = "fallback" if gpu else None
    ram_score = _ram_score(parsed.get("ram_gb"), parsed.get("ram_type"), parsed.get("ram_speed_mhz"))
    storage_score = _storage_score(parsed.get("storage_gb"), parsed.get("storage_type"))
    price_score = _price_score(parsed.get("price"), cpu_score + gpu_score * 0.45, parsed.get("ram_gb"), parsed.get("storage_gb"))

    has_dedicated_gpu = parsed.get("gpu") and gpu_score >= 30
    if has_dedicated_gpu:
        score = cpu_score * 0.35 + gpu_score * 0.3 + ram_score * 0.15 + storage_score * 0.1 + price_score * 0.1
        scoring_profile = "desktop_gpu"
    else:
        score = cpu_score * 0.5 + ram_score * 0.2 + storage_score * 0.1 + price_score * 0.2
        scoring_profile = "compact_pc"
    adjustments = []

    if cpu in PENALIZED_CPUS:
        score -= 8
        adjustments.append("CPU peu performant ou ancien")
    brand_adjustment = BRAND_ADJUSTMENTS.get(parsed.get("brand"))
    if brand_adjustment:
        brand_delta, brand_reason = brand_adjustment
        score += brand_delta
        adjustments.append(brand_reason)
    if parsed.get("ram_gb") and parsed["ram_gb"] >= 32:
        score += 4
        adjustments.append("32 Go de RAM ou plus")
    if parsed.get("ram_type") == "DDR5":
        score += 2
        adjustments.append("DDR5")
    if has_dedicated_gpu:
        adjustments.append("GPU dedie")
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
            "cpu_score_source": cpu_score_source,
            "cpu_mark": benchmark.get("cpu_mark") if benchmark else None,
            "cpu_single_thread": benchmark.get("single_thread") if benchmark else None,
            "cpu_tier": benchmark.get("tier") if benchmark else None,
            "cpu_year": cpu_release_year(cpu, benchmark),
            "gpu_score": gpu_score,
            "gpu_score_source": gpu_score_source,
            "gpu_tier": gpu_benchmark.get("tier") if gpu_benchmark else None,
            "brand_adjustment": brand_adjustment[0] if brand_adjustment else 0,
            "scoring_profile": scoring_profile,
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
    gpu = f", {parsed['gpu']}" if parsed.get("gpu") else ""

    if verdict == "À éviter":
        return f"{cpu}{gpu}, {ram}, {storage}: rapport prix/performance faible."
    if price_score >= 80:
        return f"{cpu}{gpu}, {ram}, {storage}: prix attractif pour cette configuration."
    if adjustments:
        return f"{cpu}{gpu}, {ram}, {storage}: {', '.join(adjustments[:2])}."
    return f"{cpu}{gpu}, {ram}, {storage}: configuration coherente mais prix a verifier."
