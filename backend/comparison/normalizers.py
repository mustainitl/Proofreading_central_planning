import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any, Callable


FIBRE_NAMES = {
    "cotton",
    "elastane",
    "modal",
    "polyamide",
    "polyester",
}


def is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def normalize_text(value: Any) -> str:
    if is_missing(value):
        return ""

    text = unicodedata.normalize("NFKC", str(value))
    return " ".join(text.casefold().split())


def normalize_identifier(value: Any) -> str:
    text = normalize_text(value)
    return re.sub(r"[^a-z0-9]", "", text)


def normalize_sales_order(value: Any) -> str:
    return normalize_identifier(value)


def normalize_numeric(value: Any) -> str:
    if is_missing(value):
        return ""

    number_text = str(value).replace(",", "").strip()

    try:
        number = Decimal(number_text)
    except InvalidOperation:
        return normalize_text(value)

    normalized = format(number.normalize(), "f")
    return normalized.rstrip("0").rstrip(".") if "." in normalized else normalized


def normalize_date(value: Any) -> str:
    if is_missing(value):
        return ""

    parts = [int(part) for part in re.findall(r"\d+", str(value))]

    if len(parts) != 2:
        return normalize_text(value)

    first, second = parts

    if first >= 1000:
        year, month = first, second
    elif second >= 1000:
        month, year = first, second
    else:
        month, year = first, 2000 + second

    if not 1 <= month <= 12:
        return normalize_text(value)

    return f"{year:04d}-{month:02d}"


def normalize_silhouette(value: Any) -> str:
    text = normalize_text(value)

    if not text:
        return ""

    parts = [
        re.sub(r"[^a-z0-9]+", " ", part).strip()
        for part in text.split("/")
    ]
    unique_parts = sorted({part for part in parts if part})
    return "|".join(unique_parts)


def normalize_fibre_content(value: Any) -> str:
    text = normalize_text(value)

    if not text:
        return ""

    fibre_pairs = []
    pattern = re.compile(r"(\d+(?:[.,]\d+)?)\s*%\s*([a-z]+)")

    for percentage, fibre in pattern.findall(text):
        if fibre not in FIBRE_NAMES:
            continue

        normalized_percentage = normalize_numeric(percentage.replace(",", "."))
        fibre_pairs.append((fibre, normalized_percentage))

    if not fibre_pairs:
        return text

    return "|".join(
        f"{fibre}:{percentage}"
        for fibre, percentage in sorted(fibre_pairs)
    )


NORMALIZERS: dict[str, Callable[[Any], str]] = {
    "date": normalize_date,
    "fibre_content": normalize_fibre_content,
    "identifier": normalize_identifier,
    "numeric": normalize_numeric,
    "sales_order": normalize_sales_order,
    "silhouette": normalize_silhouette,
    "text": normalize_text,
}


def normalize_value(value: Any, normalizer_name: str) -> str:
    return NORMALIZERS[normalizer_name](value)
