"""Small helper functions used by the field comparisons."""

import re
from typing import Any


def is_missing(value: Any) -> bool:
    return value is None or (
        isinstance(value, str)
        and not value.strip()
    )


def exact_status(
    work_order_value: Any,
    target_value: Any,
) -> str:
    if is_missing(work_order_value) or is_missing(target_value):
        return "missing"

    return (
        "match"
        if work_order_value == target_value
        else "mismatch"
    )


def first_ten_digit_sales_order(value: Any) -> str | None:
    if is_missing(value):
        return None

    match = re.search(r"\d{10}", str(value))
    return match.group(0) if match else None


def full_sales_order(value: Any) -> str | None:
    if is_missing(value):
        return None

    return str(value).replace(" ", "").strip()


def purchase_order_context(
    item_code: Any,
    sales_order: Any,
    po_line: Any,
) -> str:
    return (
        f"Sales Order: {sales_order or '-'} | "
        f"Item Code: {item_code or '-'} | "
        f"PO Line: {po_line or '-'}"
    )


def overall_status(statuses: list[str]) -> str:
    if not statuses:
        return "missing"

    if "mismatch" in statuses:
        return "mismatch"

    if "review" in statuses:
        return "review"

    if "missing" in statuses:
        return "missing"

    return "match"
