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


def test_desktop_gpu_scoring_profile_uses_gpu():
    parsed = parse_listing(
        "PC gamer i5 12400 RTX 3060 16 Go DDR4 3200 SSD NVMe 1To",
        650,
        "Tour fixe gaming avec RTX 3060.",
    )

    result = score_listing(parsed)

    assert parsed["gpu"] == "RTX 3060"
    assert result["details"]["gpu_score"] == 58
    assert result["details"]["scoring_profile"] == "desktop_gpu"


def test_learned_gpu_score_overrides_gpu_benchmark_when_present():
    parsed = {"cpu": "Intel i5-12400", "gpu": "RTX 3060", "ram_gb": 16, "storage_gb": 512, "storage_type": "NVMe", "price": 650}

    result = score_listing(parsed, learned_gpu_scores={"RTX 3060": 72})

    assert result["details"]["gpu_score"] == 72
    assert result["details"]["gpu_score_source"] == "learned"


def test_brand_adjustment_rewards_good_brand_and_penalizes_risky_brand():
    base = {"cpu": "Ryzen 7 5800U", "ram_gb": 16, "storage_gb": 512, "storage_type": "SSD", "price": 300}

    dell = score_listing({**base, "brand": "Dell"})
    nipogi = score_listing({**base, "brand": "NiPoGi"})

    assert dell["details"]["brand_adjustment"] == 5
    assert nipogi["details"]["brand_adjustment"] == -3
    assert dell["score"] > nipogi["score"]


def test_scoring_uses_ryzen_5700x_benchmark():
    parsed = parse_listing(
        "PC Gamer Ryzen 7 5700X 16 Go DDR4",
        "450 €",
        "Tour gamer sans GPU dedie.",
    )

    result = score_listing(parsed)

    assert parsed["cpu"] == "Ryzen 7 5700X"
    assert result["details"]["cpu_score"] == 86
    assert result["details"]["cpu_score_source"] == "benchmark"
