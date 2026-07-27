from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .matching import match_booking_sheet, match_purchase_order
from .normalizers import is_missing
from .rules import COMPARISON_RULES
from .status import comparison_status, overall_status, status_counts


def _display_value(value: Any) -> Any:
    return None if is_missing(value) else value


def _comparison_rows(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    booking_sheets: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    purchase_order_match = match_purchase_order(work_order, purchase_order)
    booking_sheet_match = match_booking_sheet(work_order, booking_sheets)
    rows = []

    for rule in COMPARISON_RULES:
        work_order_value = work_order.get(rule.work_order_key)

        if rule.target == "purchase_order":
            target_match = purchase_order_match
            purchase_order_value = target_match.values.get(rule.target_key)
            booking_sheet_value = None
            target_value = purchase_order_value
        else:
            target_match = booking_sheet_match
            purchase_order_value = None
            booking_sheet_value = target_match.values.get(rule.target_key)
            target_value = booking_sheet_value

        status = comparison_status(
            work_order_value=work_order_value,
            target_value=target_value,
            normalizer_name=rule.normalizer,
            requires_review=rule.target_key in target_match.review_fields,
        )

        rows.append(
            {
                "field": rule.field,
                "work_order": _display_value(work_order_value),
                "purchase_order": _display_value(purchase_order_value),
                "booking_sheet": _display_value(booking_sheet_value),
                "status": status,
            }
        )

    return rows


def build_comparison_response(
    work_order_documents: dict[str, list[dict[str, Any]]],
    purchase_order: dict[str, Any],
    purchase_order_file: str,
    booking_sheets: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    work_order_results = []
    all_statuses = []

    for source_file, work_orders in work_order_documents.items():
        for work_order in work_orders:
            rows = _comparison_rows(
                work_order=work_order,
                purchase_order=purchase_order,
                booking_sheets=booking_sheets,
            )
            row_statuses = [row["status"] for row in rows]
            all_statuses.extend(row_statuses)

            work_order_results.append(
                {
                    "work_order_no": (
                        work_order.get("work_order_no")
                        or Path(source_file).stem
                    ),
                    "source_file": source_file,
                    "status": overall_status(row_statuses),
                    "rows": rows,
                }
            )

    counts = status_counts(all_statuses)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "documents": {
            "work_order_files": list(work_order_documents),
            "purchase_order_file": purchase_order_file,
            "booking_sheet_files": list(booking_sheets),
        },
        "summary": {
            "overall_status": overall_status(all_statuses),
            "total_work_orders": len(work_order_results),
            "total_fields": len(all_statuses),
            **counts,
        },
        "work_orders": work_order_results,
    }
