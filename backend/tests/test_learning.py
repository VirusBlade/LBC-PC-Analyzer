from app.learning import detect_flags
from app.parser import parse_listing
from app.scoring import score_listing


def test_detect_flags_for_unknown_listing_parts():
    parsed = parse_listing("Mini PC mystere", "199 €", "ordinateur compact")
    result = {**parsed, **score_listing(parsed)}

    flags = detect_flags(result)

    assert "missing_cpu" in flags
    assert "missing_ram" in flags
    assert "missing_storage" in flags


def test_detect_flags_for_known_good_listing():
    parsed = parse_listing("Beelink Ryzen 7 5800U 16 Go SSD de 512 Go", "300 €", "mini pc")
    result = {**parsed, **score_listing(parsed)}

    flags = detect_flags(result)

    assert "missing_cpu" not in flags
    assert "missing_ram" not in flags
    assert "missing_storage" not in flags


def test_learning_suggestions_shape():
    from app.learning import get_suggestions

    suggestions = get_suggestions(limit=5)

    assert "cpu_candidates" in suggestions
    assert "brand_candidates" in suggestions
    assert "storage_snippets" in suggestions
