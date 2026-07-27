from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .normalizers import (
    is_missing,
    normalize_fibre_content,
    normalize_identifier,
    normalize_sales_order,
    normalize_silhouette,
)


BOOKING_SILHOUETTE_KEY = "Seasonless - Silhouette Code"
BOOKING_CONTENT_KEY = "Seasonless - Product Content Summary"


@dataclass
class MatchedValues:
    values: dict[str, Any] = field(default_factory=dict)
    review_fields: set[str] = field(default_factory=set)


def _joined_values(values: list[Any]) -> str | None:
    unique_values = []

    for value in values:
        if is_missing(value) or value in unique_values:
            continue
        unique_values.append(value)

    if not unique_values:
        return None

    return ", ".join(str(value) for value in unique_values)


def _order_line(order: dict[str, Any]) -> str | None:
    line_values = [
        size.get("po_line")
        for size in order.get("sizes", [])
        if not is_missing(size.get("po_line"))
    ]
    return _joined_values(line_values)


def _order_quantity(order: dict[str, Any]) -> int | float | None:
    quantities = [
        size.get("quantity")
        for size in order.get("sizes", [])
        if not is_missing(size.get("quantity"))
    ]

    if not quantities:
        return None

    total = sum(Decimal(str(quantity)) for quantity in quantities)
    return int(total) if total == total.to_integral() else float(total)


def match_purchase_order(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
) -> MatchedValues:
    result = MatchedValues(
        values={
            "po_number": purchase_order.get("po_number"),
            "factory_id": purchase_order.get("factory_id"),
            "date_of_mfr": purchase_order.get("date_of_mfr"),
            "item_code": None,
            "so_number": None,
            "line_item": None,
            "quantity": None,
        }
    )

    items = purchase_order.get("items", [])
    expected_item_code = normalize_identifier(work_order.get("item_code"))
    matching_items = [
        item
        for item in items
        if normalize_identifier(item.get("item_code")) == expected_item_code
    ]

    if len(matching_items) == 0:
        result.values["item_code"] = _joined_values(
            [item.get("item_code") for item in items]
        )
        return result

    if len(matching_items) > 1:
        result.review_fields.update(
            {"item_code", "so_number", "line_item", "quantity"}
        )
        return result

    matched_item = matching_items[0]
    result.values["item_code"] = matched_item.get("item_code")

    orders = matched_item.get("sales_orders", [])
    expected_sales_order = normalize_sales_order(work_order.get("so_number"))
    matching_orders = [
        order
        for order in orders
        if normalize_sales_order(order.get("sales_order"))
        == expected_sales_order
    ]

    if len(matching_orders) == 0:
        result.values["so_number"] = _joined_values(
            [order.get("sales_order") for order in orders]
        )
        return result

    if len(matching_orders) > 1:
        result.review_fields.update({"so_number", "line_item", "quantity"})
        return result

    matched_order = matching_orders[0]
    result.values["so_number"] = matched_order.get("sales_order")
    result.values["line_item"] = _order_line(matched_order)
    result.values["quantity"] = _order_quantity(matched_order)
    return result


def _booking_identity(row: dict[str, Any]) -> tuple[str, str]:
    return (
        normalize_silhouette(row.get(BOOKING_SILHOUETTE_KEY)),
        normalize_fibre_content(row.get(BOOKING_CONTENT_KEY)),
    )


def match_booking_sheet(
    work_order: dict[str, Any],
    booking_sheets: dict[str, list[dict[str, Any]]],
) -> MatchedValues:
    result = MatchedValues(
        values={
            "silhouette": None,
            "garment_components": None,
        }
    )

    rows = [
        row
        for sheet_rows in booking_sheets.values()
        for row in sheet_rows
    ]
    expected_silhouette = normalize_silhouette(work_order.get("silhouette"))
    matching_rows = [
        row
        for row in rows
        if normalize_silhouette(row.get(BOOKING_SILHOUETTE_KEY))
        == expected_silhouette
    ]

    if len(matching_rows) == 0:
        result.values["silhouette"] = _joined_values(
            [row.get(BOOKING_SILHOUETTE_KEY) for row in rows]
        )
        return result

    unique_rows: dict[tuple[str, str], dict[str, Any]] = {}

    for row in matching_rows:
        unique_rows.setdefault(_booking_identity(row), row)

    if len(unique_rows) > 1:
        result.review_fields.update({"silhouette", "garment_components"})
        return result

    matched_row = next(iter(unique_rows.values()))
    result.values["silhouette"] = matched_row.get(BOOKING_SILHOUETTE_KEY)
    result.values["garment_components"] = matched_row.get(BOOKING_CONTENT_KEY)
    return result
