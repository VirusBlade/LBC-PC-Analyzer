from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CPU_BENCHMARKS_PATH = Path(__file__).with_name("cpu_benchmarks.json")


@lru_cache(maxsize=1)
def load_cpu_benchmarks() -> dict[str, dict[str, Any]]:
    if not CPU_BENCHMARKS_PATH.exists():
        return {}
    data = json.loads(CPU_BENCHMARKS_PATH.read_text())
    return data.get("cpus", {})


def get_cpu_benchmark(cpu: str | None) -> dict[str, Any] | None:
    if not cpu:
        return None
    return load_cpu_benchmarks().get(cpu)


def cpu_score_from_benchmark(cpu: str | None) -> tuple[int | None, dict[str, Any] | None]:
    benchmark = get_cpu_benchmark(cpu)
    if not benchmark:
        return None, None
    if "score" in benchmark:
        return int(benchmark["score"]), benchmark
    cpu_mark = benchmark.get("cpu_mark")
    if not cpu_mark:
        return None, benchmark
    return max(0, min(100, round(float(cpu_mark) / 240))), benchmark
