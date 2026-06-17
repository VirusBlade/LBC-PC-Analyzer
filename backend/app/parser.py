from __future__ import annotations

import re
from typing import Any


CUSTOM_PC_BRAND = "PC Custom"

BRANDS = [
    "Beelink",
    "Minisforum",
    "GMKtec",
    "Geekom",
    "Chuwi",
    "Lenovo",
    "HP",
    "Dell",
    "Shuttle",
    "NiPoGi",
    "Acemagic",
    "Ace Magician",
    "Intel",
    "MSI",
    "Schneider",
]

CPU_ALIASES = {
    "RYZEN 7 5700U": "Ryzen 7 5700U",
    "RYZEN 7 5700X": "Ryzen 7 5700X",
    "RYZEN 7 5800H": "Ryzen 7 5800H",
    "RYZEN 7 5800U": "Ryzen 7 5800U",
    "RYZEN 7 8700G": "Ryzen 7 8700G",
    "RYZEN 7 H255": "Ryzen 7 H255",
    "RYZEN 7 6800U": "Ryzen 7 6800U",
    "RYZEN 9 6900HX": "Ryzen 9 6900HX",
    "RYZEN 7 7735HS": "Ryzen 7 7735HS",
    "RYZEN 7 8745HS": "Ryzen 7 8745HS",
    "RYZEN 5 7430U": "Ryzen 5 7430U",
    "RYZEN 5 5500U": "Ryzen 5 5500U",
    "RYZEN 5 5650GE": "Ryzen 5 5650GE",
    "I5 6500T": "Intel i5-6500T",
    "I5 7500": "Intel i5-7500",
    "I5 8500T": "Intel i5-8500T",
    "I5 9500": "Intel i5-9500",
    "I5 1135G7": "Intel i5-1135G7",
    "I5 12400": "Intel i5-12400",
    "I5 1235U": "Intel i5-1235U",
    "I5 1250P": "Intel i5-1250P",
    "N100": "Intel N100",
    "N150": "Intel N150",
    "N4000": "Intel N4000",
    "I7 6700HQ": "Intel i7-6700HQ",
    "G630": "Intel G630",
    "A10": "AMD A10",
}


def normalize_text(*parts: Any) -> str:
    text = " ".join(str(part or "") for part in parts)
    text = text.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", text).strip()


def parse_price(value: Any, text: str = "") -> int | None:
    if isinstance(value, (int, float)):
        return int(value)

    source = normalize_text(value, text)
    matches = re.findall(r"(\d[\d\s.,]{0,8})\s*(?:EUR|€|euros?)", source, re.I)
    if not matches:
        return None

    cleaned = re.sub(r"[^\d]", "", matches[0])
    return int(cleaned) if cleaned else None


def looks_like_custom_pc(text: str) -> bool:
    custom_patterns = [
        r"\bPC\s*(?:custom|gamer|gaming|fixe|monte|mont[ée]|assemble|assembl[ée])\b",
        r"\b(?:tour|config|configuration)\s*(?:gamer|gaming|custom|montee|mont[ée]e|assemblee|assembl[ée]e)?\b",
        r"\bcarte\s+(?:mere|m[èe]re|graphique)\b",
        r"\b(?:boitier|alimentation|watercooling|ventirad)\b",
    ]
    return any(re.search(pattern, text, re.I) for pattern in custom_patterns) and not re.search(
        r"\b(Beelink|Minisforum|GMKtec|Geekom|Chuwi|Lenovo|Dell|Shuttle|NiPoGi|Acemagic|Ace\s+Magician)\b|\bHP\s+(?:EliteDesk|ProDesk|Pavilion|Compaq|Z\d|Elitedesk|Prodesk)\b",
        text,
        re.I,
    )


def extract_brand(text: str) -> str | None:
    if looks_like_custom_pc(text):
        return CUSTOM_PC_BRAND

    for brand in BRANDS:
        if brand == "HP" and not re.search(r"\bHP\s+(?:EliteDesk|ProDesk|Pavilion|Compaq|Z\d|Elitedesk|Prodesk)\b", text, re.I):
            continue
        if re.search(rf"\b{re.escape(brand)}\b", text, re.I):
            return "Acemagic" if brand == "Ace Magician" else brand
    return None


def extract_cpu(text: str) -> str | None:
    upper = text.upper()
    upper = re.sub(r"[-_/]+", " ", upper)
    upper = re.sub(r"\s+", " ", upper)

    for key, label in CPU_ALIASES.items():
        if re.search(rf"\b{re.escape(key)}\b", upper):
            return label

    if re.search(r"\b8745HS\b", upper):
        return "Ryzen 7 8745HS"
    if re.search(r"\bUM690\b", upper) and re.search(r"\bRYZEN\s*9\b", upper):
        return "Ryzen 9 6900HX"

    ryzen = re.search(r"\bRYZEN\s*([3579])\s*((?:\d{4}|H\s*\d{3})[A-Z]{0,2})\b", upper)
    if ryzen:
        return f"Ryzen {ryzen.group(1)} {ryzen.group(2).replace(' ', '')}"

    ryzen_family = re.search(r"\bRYZEN\s*([3579])\b", upper)
    if ryzen_family:
        return f"Ryzen {ryzen_family.group(1)} unknown"

    intel_gen = re.search(r"\b(?:INTEL\s*)?I([357])\s*(\d{1,2})(?:TH)?\s*(?:GEN)?\b", upper)
    if intel_gen and int(intel_gen.group(2)) <= 14:
        return f"Intel i{intel_gen.group(1)}-{intel_gen.group(2)}th gen"

    intel_core = re.search(r"\b(?:INTEL\s*)?I\s*\.?\s*([357])\s*(\d{4,5}[A-Z]{0,2})\b", upper)
    if intel_core:
        return f"Intel i{intel_core.group(1)}-{intel_core.group(2)}"

    split_intel_core = re.search(r"\bI\s*\.?\s*([357])\b.{0,12}\b(\d{4,5}[A-Z]{0,2})\b", upper)
    if split_intel_core:
        return f"Intel i{split_intel_core.group(1)}-{split_intel_core.group(2)}"

    intel_n = re.search(r"\b(?:INTEL\s*)?N(100|150|4000)\b", upper)
    if intel_n:
        return f"Intel N{intel_n.group(1)}"

    pentium = re.search(r"\b(?:INTEL\s*)?G(630)\b", upper)
    if pentium:
        return f"Intel G{pentium.group(1)}"

    return None


def extract_ram_gb(text: str) -> int | None:
    candidates: list[int] = []
    storage_words = r"SSD|NVME|HDD|STOCKAGE|DISQUE|STORAGE|ROM|EMMC|SATA|M\.2|M2|DD"

    for left, right in re.findall(r"\b(\d{1,2})\s*x\s*(\d{1,2})\b", text, re.I):
        candidates.append(int(left) * int(right))

    for match in re.finditer(r"\b(\d{1,3})\s*(?:GO|GB)\b", text, re.I):
        before = text[max(0, match.start() - 42) : match.start()]
        after = text[match.end() : min(len(text), match.end() + 28)]
        gb = int(match.group(1))
        context = f"{before} {match.group(0)} {after}"
        ram_context = re.search(r"\b(RAM|DDR\d?|MEMOIRE|MÉMOIRE|MEMORY|BARRETTE|SO\s*DIMM|SODIMM)\b", context, re.I)
        storage_context = re.search(storage_words, context, re.I)
        if re.search(r"\b(jusqu['’]?a|jusqu[àa]|max(?:imum)?|extension\s+possible|supporte?)\b", before, re.I):
            continue
        storage_before = rf"\b({storage_words})\s*(?::|de|d\'|avec|en)?\s*$"
        storage_after = rf"^\s*(SSD|NVME|HDD|ROM|EMMC|SATA|M\.2|M2|DD)\b"
        if re.search(storage_before, before, re.I) or (gb >= 64 and (re.search(storage_after, after, re.I) or (storage_context and not ram_context))):
            continue
        if 2 <= gb <= 128:
            candidates.append(gb)

    for match in re.finditer(r"\b(\d{1,3})\s*G\b", text, re.I):
        gb = int(match.group(1))
        context = text[max(0, match.start() - 24) : min(len(text), match.end() + 24)]
        if 2 <= gb <= 128 and re.search(r"\b(RAM|DDR[345]|MEMOIRE|MÉMOIRE|MEMORY)\b", context, re.I):
            candidates.append(gb)

    return max(candidates) if candidates else None



def extract_ram_details(text: str) -> dict[str, Any]:
    ram_type = None
    ram_speed_mhz = None

    type_match = re.search(r"\b(DDR[345])\b", text, re.I)
    if type_match:
        ram_type = type_match.group(1).upper()

    speed_patterns = [
        r"\b(DDR[345])[-\s]*(\d{4,5})\s*(?:MHZ)?\b",
        r"\b(\d{4,5})\s*MHZ\b",
    ]
    for pattern in speed_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            ram_speed_mhz = int(match.group(match.lastindex))
            break

    return {"ram_type": ram_type, "ram_speed_mhz": ram_speed_mhz}


def extract_gpu(text: str) -> str | None:
    upper = text.upper()
    patterns = [
        (r"\bRTX\s*(5090|5080|5070|4070|4060|3090|3080|3070|3060|2080|2070|2060)\b", "RTX {}"),
        (r"\bGTX\s*(1660\s*SUPER|1660|1650|1060|970|1050\s*TI)\b", "GTX {}"),
        (r"\b(?:RX\s*)?(9070\s*XT)\b", "RX {}"),
        (r"\bRX\s*(7900\s*XTX|7800\s*XT|7700\s*XT|7600|6800\s*XT|6750\s*XT|6700\s*XT|6600|5700\s*XT)\b", "RX {}"),
        (r"\bRADEON\s*(780M)\b", "Radeon {}"),
        (r"\bARC\s*(A770|A750)\b", "Intel Arc {}"),
    ]
    for pattern, template in patterns:
        match = re.search(pattern, upper, re.I)
        if match:
            value = re.sub(r"\s+", " ", match.group(1).upper()).strip()
            value = re.sub(r"^(\d{4})(XT|XTX)$", r"\1 \2", value)
            return template.format(value)
    return None


def _size_to_gb(value: str, unit: str) -> int:
    number = float(value.replace(",", "."))
    normalized_unit = unit.lower()
    if normalized_unit.startswith("t"):
        return int(number * 1024)
    return int(number)


def extract_storage(text: str) -> dict[str, Any]:
    candidates = []
    storage_words = r"SSD|NVME|NVM\s*E|M\.2|M2|HDD|EMMC|SATA|STOCKAGE|DISQUE|STORAGE|ROM|FLASH|DRIVE|DD"
    ram_words = r"RAM|DDR\d?|MEMOIRE|MÉMOIRE|MEMORY|BARRETTE|SO\s*DIMM|SODIMM"
    size_pattern = re.compile(r"\b(\d+(?:[,.]\d+)?)\s*(TO|TB|GO|GB)\b", re.I)

    for match in size_pattern.finditer(text):
        value, unit = match.groups()
        size_gb = _size_to_gb(value, unit)
        if not 32 <= size_gb <= 8192:
            continue

        before = text[max(0, match.start() - 40) : match.start()]
        after = text[match.end() : min(len(text), match.end() + 28)]
        context = f"{before} {after}"
        nearest_before = re.search(rf"\b({storage_words})\s*(?::|de|d\'|avec|en)?\s*$", before, re.I)
        nearest_after = re.search(rf"^\s*(?:[:/+-]\s*)?({storage_words})\b", after, re.I)

        if nearest_before:
            token = nearest_before.group(1)
        elif nearest_after:
            token = nearest_after.group(1)
        else:
            # Bare capacities like "16 Go 512 Go" or "Samsung 990 Pro 1To"
            # are common. Ignore RAM-sized bare values, but keep storage-sized ones
            # even when DDR/RAM appears elsewhere in the same title.
            if size_gb < 128:
                continue
            token = "SSD"

        kind = _storage_kind_from_token(token.upper().replace(" ", ""))
        confidence = 3 if nearest_before or nearest_after else 1
        if re.search(r"\bEMMC\b", context, re.I):
            kind = "eMMC"
            confidence += 1
        if re.search(r"\b(NVME|NVM\s*E|M\.2|M2)\b", context, re.I):
            if kind == "SSD":
                kind = "NVMe"
            confidence += 1
        if re.search(r"\b(SSD|NVME|NVM\s*E|M\.2|M2)\b", context, re.I):
            confidence += 1

        candidates.append({"type": kind, "size_gb": size_gb, "confidence": confidence})

    if not candidates:
        return {"type": None, "size_gb": None, "label": None}

    best = max(candidates, key=lambda item: (item["size_gb"], item["confidence"]))
    label_size = f"{best['size_gb'] // 1024} To" if best["size_gb"] >= 1024 and best["size_gb"] % 1024 == 0 else f"{best['size_gb']} Go"
    return {"type": best["type"], "size_gb": best["size_gb"], "label": f"{best['type']} {label_size}"}


def _storage_kind_from_token(token: str) -> str:
    if token in {"NVME", "NVME", "M.2", "M2"}:
        return "NVMe"
    if token == "SATA":
        return "SATA SSD"
    if token in {"HDD", "DD"}:
        return "HDD"
    if token == "EMMC":
        return "eMMC"
    return "SSD"

def extract_model(title: str, brand: str | None, cpu: str | None) -> str | None:
    model = title or ""
    if brand:
        model = re.sub(rf"\b{re.escape(brand)}\b", "", model, flags=re.I)
    if cpu:
        cpu_token = re.escape(cpu.replace("Intel ", "").replace("-", " "))
        model = re.sub(cpu_token, "", model, flags=re.I)
    model = re.sub(r"\b(mini\s*pc|pc|ordinateur|ryzen|intel|custom)\b", "", model, flags=re.I)
    model = re.sub(r"\b\d+\s*(go|gb|to|tb)\b", "", model, flags=re.I)
    model = re.sub(r"\s+", " ", model).strip(" -,:")
    return model[:80] or None


def parse_listing(title: str, price: Any = None, description: str = "") -> dict[str, Any]:
    text = normalize_text(title, price if isinstance(price, str) else "", description)
    brand = extract_brand(text)
    cpu = extract_cpu(text)
    ram_gb = extract_ram_gb(text)
    ram_details = extract_ram_details(text)
    storage = extract_storage(text)
    gpu = extract_gpu(text)
    parsed_price = parse_price(price, text)

    return {
        "brand": brand,
        "model": extract_model(title, brand, cpu),
        "cpu": cpu,
        "ram_gb": ram_gb,
        "ram_type": ram_details["ram_type"],
        "ram_speed_mhz": ram_details["ram_speed_mhz"],
        "gpu": gpu,
        "storage_type": storage["type"],
        "storage_gb": storage["size_gb"],
        "storage_label": storage["label"],
        "price": parsed_price,
        "raw": {"title": title, "description": description},
    }
