from app.parser import parse_listing
from app.scoring import score_listing


def test_scoring_uses_local_cpu_benchmark_details():
    parsed = parse_listing(
        "Mini PC Ace Magician AM06 Pro Ryzen 7 5800U 16 Go SSD 512 Go",
        "300 €",
        "Ryzen 7 5800U, 16 Go RAM, SSD de 512 Go.",
    )

    result = score_listing(parsed)

    assert result["details"]["cpu_score"] == 79
    assert result["details"]["cpu_score_source"] == "benchmark"
    assert result["details"]["cpu_mark"] is not None


def test_learned_cpu_score_overrides_benchmark_when_present():
    parsed = {"cpu": "Ryzen 7 5800U", "ram_gb": 16, "storage_gb": 512, "storage_type": "SSD", "price": 300}

    result = score_listing(parsed, learned_cpu_scores={"Ryzen 7 5800U": 88})

    assert result["details"]["cpu_score"] == 88
    assert result["details"]["cpu_score_source"] == "learned"
