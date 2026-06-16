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


def test_parse_desktop_pc_with_radeon_rx_5700_xt_without_space():
    parsed = parse_listing(
        "PC gamer Ryzen 5 5600 16 Go DDR4",
        "500 €",
        "Carte graphique : Radeon RX 5700XT 8go, SSD 1To.",
    )

    assert parsed["gpu"] == "RX 5700 XT"
    assert parsed["ram_gb"] == 16
    assert parsed["storage_gb"] == 1024


def test_parse_custom_pc_does_not_confuse_ssd_120go_with_ram():
    parsed = parse_listing(
        "PC gamer i5-7400 GTX 1060",
        "250 €",
        """
        Carte Mère :MSI H110m pro-vd
        Processeur : Intel Core i5-7400
        Mémoire Ram : Corsair Vengeance LPX DDR4 RAM 32Go (2x16Go)
        Carte Graphique : MSI GTX 1060 GAMING X
        SSD Corsair 120 GO ( Windows 11 pro installé dessus )
        SSD 120 GO
        HDD 1 TO
        Alimentation 550 W
        """,
    )

    assert parsed["cpu"] == "Intel i5-7400"
    assert parsed["gpu"] == "GTX 1060"
    assert parsed["ram_gb"] == 32
    assert parsed["ram_type"] == "DDR4"
    assert parsed["storage_gb"] == 1024
    assert parsed["storage_type"] == "HDD"


def test_parse_installed_ram_ignores_max_supported_ram():
    parsed = parse_listing(
        "Intel NUC",
        "120 €",
        """
        Processeur : Intel Core i3-8109U
        Mémoire vive (RAM) : --> 16 Go (extension possible jusqu'à 32 Go max; barrettes SO-DIMM DDR4-2400)
        Baie de stockage 2,5\" : --> 180 Go Intel SSD
        """,
    )

    assert parsed["cpu"] == "Intel i3-8109U"
    assert parsed["ram_gb"] == 16
    assert parsed["ram_type"] == "DDR4"
    assert parsed["ram_speed_mhz"] == 2400
    assert parsed["storage_label"] == "SSD 180 Go"


def test_parse_old_gamer_tower_i7_4790k_gtx_970():
    parsed = parse_listing(
        "PC GAMER et Polyvalent petit prix",
        "295€",
        """
        Le prix indiqué est pour la tour seule (295€)
        pour le tout: tour écran, clavier, souris, HP; Le prix est 345€
        Carte mère micro ATX
        Cpu intel core I7 4790k à 4Ghz
        16 Go ram DDr3
        Carte graphique GTX 970 4go
        SSD Samsung 500 go pour Windows11
        HDD 1 to pour le stockage des jeux
        """,
    )

    assert parsed["brand"] == "PC Custom"
    assert parsed["cpu"] == "Intel i7-4790K"
    assert parsed["gpu"] == "GTX 970"
    assert parsed["ram_gb"] == 16
    assert parsed["ram_type"] == "DDR3"
    assert parsed["storage_gb"] == 1024
    assert parsed["storage_type"] == "HDD"


def test_custom_pc_does_not_use_motherboard_brand():
    parsed = parse_listing(
        "PC custom Ryzen 5 5600 RX 6750 XT 32 Go",
        "700 €",
        "Carte mere MSI B550, alimentation Corsair, boitier NZXT.",
    )

    assert parsed["brand"] == "PC Custom"
    assert parsed["gpu"] == "RX 6750 XT"


def test_parse_ryzen_7_5700x():
    parsed = parse_listing(
        "PC Gamer Ryzen 7 5700X MSI B550 16 Go DDR4",
        "450 €",
        "Tour gamer sans carte graphique dediee.",
    )

    assert parsed["cpu"] == "Ryzen 7 5700X"
    assert parsed["brand"] == "PC Custom"
