from app.parser import parse_listing


def test_parse_desktop_pc_with_gpu_ddr5_and_nvme():
    parsed = parse_listing(
        "PC gamer Ryzen 5 5600 RTX 3060 32Go DDR5 6000MHz SSD M.2 NVMe 1To",
        "650 €",
        "Tour fixe, non portable, RTX 3060, NVMe 1 To.",
    )

    assert parsed["gpu"] == "RTX 3060"
    assert parsed["ram_gb"] == 32
    assert parsed["ram_type"] == "DDR5"
    assert parsed["ram_speed_mhz"] == 6000
    assert parsed["storage_type"] == "NVMe"
    assert parsed["storage_gb"] == 1024


def test_parse_desktop_pc_with_sata_ssd_and_amd_gpu():
    parsed = parse_listing(
        "PC fixe i5 12400 RX 6700 XT 16 Go DDR4 3200 SSD SATA 512 Go",
        520,
        "Ordinateur de bureau avec SSD SATA.",
    )

    assert parsed["cpu"] == "Intel i5-12400"
    assert parsed["gpu"] == "RX 6700 XT"
    assert parsed["ram_type"] == "DDR4"
    assert parsed["ram_speed_mhz"] == 3200
    assert parsed["storage_type"] == "SATA SSD"


def test_parse_desktop_pc_with_radeon_rx_6750_xt():
    parsed = parse_listing(
        "PC custom Ryzen 5 5600 Carte Graphique AMD Radeon Rx6750xt 32 Go DDR4 SSD 1To",
        "700 €",
        "Tour gamer avec Carte Graphique AMD Radeon RX 6750 XT.",
    )

    assert parsed["gpu"] == "RX 6750 XT"
    assert parsed["ram_gb"] == 32
    assert parsed["storage_gb"] == 1024


def test_custom_pc_does_not_use_motherboard_brand():
    parsed = parse_listing(
        "PC custom Ryzen 5 5600 RX 6750 XT 32 Go",
        "700 €",
        "Carte mere MSI B550, alimentation Corsair, boitier NZXT.",
    )

    assert parsed["brand"] == "PC Custom"
    assert parsed["gpu"] == "RX 6750 XT"
