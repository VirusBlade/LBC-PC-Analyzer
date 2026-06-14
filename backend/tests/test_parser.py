from app.parser import parse_listing
from app.scoring import score_listing


def test_parse_ryzen_beelink_ram_and_nvme():
    parsed = parse_listing(
        "Beelink SER5 Ryzen 7 5700U 16Go 512Go SSD",
        "280 €",
        "Mini PC avec NVMe 512 Go, tres bon etat.",
    )

    assert parsed["brand"] == "Beelink"
    assert parsed["cpu"] == "Ryzen 7 5700U"
    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert parsed["price"] == 280


def test_parse_2x8_and_intel_dash_format():
    parsed = parse_listing(
        "Lenovo ThinkCentre i5-8500T",
        160,
        "RAM 2x8, SSD 256GB, Windows 11.",
    )

    assert parsed["brand"] == "Lenovo"
    assert parsed["cpu"] == "Intel i5-8500T"
    assert parsed["ram_gb"] == 16
    assert parsed["storage_label"] == "SSD 256 Go"


def test_parse_terabyte_hdd_and_32gb():
    parsed = parse_listing(
        "Minisforum UM690 Ryzen 9 6900HX",
        "449 euros",
        "32GB DDR5 et SSD 1To + HDD 2To externe.",
    )

    assert parsed["cpu"] == "Ryzen 9 6900HX"
    assert parsed["ram_gb"] == 32
    assert parsed["storage_gb"] == 2048
    assert parsed["storage_type"] == "HDD"


def test_score_penalizes_n100_but_returns_verdict():
    parsed = parse_listing("Mini PC Intel N100 8go SSD 256 Go", 220, "NiPoGi")
    result = score_listing(parsed)

    assert 0 <= result["score"] <= 100
    assert result["verdict"] in {"Excellent", "Bon", "Moyen", "À éviter"}
    assert result["details"]["cpu_score"] == 30


def test_parse_storage_label_without_ssd_keyword():
    parsed = parse_listing(
        "Mini PC Ryzen 5 5500U 16 Go",
        "210 €",
        "Stockage : 512 Go. Memoire RAM 16 Go.",
    )

    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert parsed["storage_label"] == "SSD 512 Go"


def test_parse_bare_storage_after_ram_in_title():
    parsed = parse_listing(
        "Mini PC N100 16Go 512Go Windows 11",
        "150 €",
        "Petit ordinateur bureautique.",
    )

    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert parsed["storage_label"] == "SSD 512 Go"


def test_parse_rom_and_emmc_storage():
    parsed = parse_listing(
        "Chuwi LarkBox Intel N100",
        "120 €",
        "8GB RAM / 256GB ROM eMMC extensible.",
    )

    assert parsed["ram_gb"] == 8
    assert parsed["storage_gb"] == 256
    assert parsed["storage_type"] == "eMMC"


def test_parse_m2_nvme_storage_without_space():
    parsed = parse_listing(
        "Minisforum UM790",
        499,
        "32 Go DDR5, disque M.2 NVMe 1To, Ryzen 7.",
    )

    assert parsed["ram_gb"] == 32
    assert parsed["storage_gb"] == 1024
    assert parsed["storage_type"] == "NVMe"


def test_parse_multiple_storage_sizes_keeps_largest():
    parsed = parse_listing(
        "Dell Optiplex i5-9500",
        180,
        "16 Go RAM, SSD 256 Go + HDD 1 To.",
    )

    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 1024
    assert parsed["storage_type"] == "HDD"


def test_parse_storage_with_de_connector():
    parsed = parse_listing(
        "Mini PC Beelink Ryzen 7 5700U 16 Go",
        "260 €",
        "Vendu avec un SSD de 512 Go et 16 Go de RAM.",
    )

    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert parsed["storage_label"] == "SSD 512 Go"


def test_parse_nvme_with_de_connector():
    parsed = parse_listing(
        "Minisforum Ryzen 7 6800U 32 Go",
        420,
        "Stockage NVMe de 1 To, RAM DDR5 32 Go.",
    )

    assert parsed["ram_gb"] == 32
    assert parsed["storage_gb"] == 1024
    assert parsed["storage_type"] == "NVMe"


def test_parse_ram_before_ssd_de_storage():
    parsed = parse_listing(
        "Mini PC Intel N100 16 Go SSD de 512 Go",
        180,
        "Beelink.",
    )

    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert parsed["storage_label"] == "SSD 512 Go"


def test_parse_ace_magician_5800u_listing():
    parsed = parse_listing(
        "Mini PC Ace Magician AM06 Pro - Ryzen 7 5800U - 16 Go RAM - 512 Go SSD",
        "300 €",
        "AMD Ryzen 7 5800U, 16 Go de RAM et SSD de 512 Go.",
    )
    scored = score_listing(parsed)

    assert parsed["brand"] == "Acemagic"
    assert parsed["cpu"] == "Ryzen 7 5800U"
    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 512
    assert scored["details"]["cpu_score"] == 79
    assert scored["score"] >= 75


def test_parse_search_examples_new_cpu_base():
    examples = [
        ("Mini PC Minisforum MS-A1 - Ryzen 7 8700G / 48Go DDR5 / Samsung 990 Pro 1To", "Ryzen 7 8700G", 48, 1024),
        ("Mini PC GMKtec K12 Ryzen 7 H255, 32 Go DDR5 / SSD 1To", "Ryzen 7 H255", 32, 1024),
        ("MINI PC Dell OPTIPLEX 5050 Core i5 7500 2.70 Ghz 16Go Ram SSD 250 Go", "Intel i5-7500", 16, 250),
        ("MINI PC Dell OPTIPLEX 5050 Core i5 6500T 2.70 Ghz 8 Go Ram SSD 250 Go", "Intel i5-6500T", 8, 250),
        ("Core i5-1235U 8 Go DDR4 / SSD 256 Go", "Intel i5-1235U", 8, 256),
        ("Mini-PC Stick Windows 11 Pro Intel N4000 RAM 4GB SSD 64GB", "Intel N4000", 4, 64),
        ("Nuc Skull canyon / i.7 / mini gamer / 6700hq", "Intel i7-6700HQ", None, None),
        ("PC HP Compaq 6200 Pro SFF Intel G630 RAM 8Go Disque Dur 500Go", "Intel G630", 8, 500),
    ]

    for title, cpu, ram, storage in examples:
        parsed = parse_listing(title, "199 €", title)
        assert parsed["cpu"] == cpu
        assert parsed["ram_gb"] == ram
        assert parsed["storage_gb"] == storage


def test_parse_more_search_inferred_cpus():
    cases = [
        ("Mini PC Barebone Chuwi Aubox / 8745hs / oculink / neuf", "Ryzen 7 8745HS", None, None),
        ("Mini PC Chuwi UBOX amd ryzen 5 16 go ram 512 go ssd", "Ryzen 5 unknown", 16, 512),
        ("Mini PC Minisforum UM690 Slim - Ryzen 9 / 32 Go RAM DDR5 / 1TB SSD", "Ryzen 9 6900HX", 32, 1024),
        ("Mini Hp Prodesk 400 G6 i3 10th 8 Go 256 Go windows 11 wifi intégré", "Intel i3-10th gen", 8, 256),
    ]

    for title, cpu, ram, storage in cases:
        parsed = parse_listing(title, "199 €", title)
        assert parsed["cpu"] == cpu
        assert parsed["ram_gb"] == ram
        assert parsed["storage_gb"] == storage
