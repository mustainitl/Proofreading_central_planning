"""Simple field-by-field comparisons for the three extracted datasets."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.comparison_helpers import (
    exact_status,
    first_ten_digit_sales_order,
    full_sales_order,
    is_missing,
    mfr_date_status,
    overall_status,
    product_code_status,
    purchase_order_context,
    vsd_status,
)

# -------------------------------------------------------------------------
# PO Number comparison
# -------------------------------------------------------------------------
def compare_po_number(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("vs_po_number")
    purchase_order_value = purchase_order.get("po_number")

    comparison_context["po_number"] = {
        "work_order": work_order_value,
        "purchase_order": purchase_order_value,
        "status": exact_status(
            work_order_value,
            purchase_order_value,
        ),
    }

    return {
        "field": "PO Number",
        "work_order": work_order_value,
        "purchase_order": purchase_order_value,
        "booking_sheet": None,
        "status": exact_status(
            work_order_value,
            purchase_order_value,
        ),
    }

# -------------------------------------------------------------------------
# Customer Order Number comparison
# -------------------------------------------------------------------------
def compare_customer_order_number(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    customer_order_no = work_order.get("customer_order_no")
    work_order_item_code = str(work_order.get("item_code") or "").strip()
    work_order_sales_order_raw = work_order.get("so_number")
    work_order_sales_order_10_digit = first_ten_digit_sales_order(
        work_order_sales_order_raw
    )
    work_order_sales_order_full = full_sales_order(
        work_order_sales_order_raw
    )
    work_order_po_line = str(work_order.get("line_item") or "").strip()

    customer_order_checks = {
        "item_code": {
            "work_order": work_order.get("item_code"),
            "purchase_order": None,
            "status": (
                "missing"
                if is_missing(work_order_item_code)
                else "mismatch"
            ),
        },
        "sales_order": {
            "work_order": work_order_sales_order_10_digit,
            "purchase_order": None,
            "status": (
                "missing"
                if is_missing(work_order_sales_order_10_digit)
                else "mismatch"
            ),
        },
        "po_line": {
            "work_order": work_order.get("line_item"),
            "purchase_order": None,
            "status": (
                "missing"
                if is_missing(work_order_po_line)
                else "mismatch"
            ),
        },
    }
    comparison_context["customer_order_number"] = customer_order_checks
    comparison_context["individual_sales_order"] = {
        "work_order": work_order_sales_order_raw,
        "purchase_order": None,
        "status": (
            "missing"
            if is_missing(work_order_sales_order_full)
            else "mismatch"
        ),
    }

    purchase_order_value = None

    for item in purchase_order.get("items", []):
        item_code = str(item.get("item_code") or "").strip()

        if is_missing(item_code):
            continue

        if is_missing(customer_order_checks["item_code"]["purchase_order"]):
            customer_order_checks["item_code"]["purchase_order"] = item_code

        if item_code != work_order_item_code:
            continue

        customer_order_checks["item_code"] = {
            "work_order": work_order.get("item_code"),
            "purchase_order": item_code,
            "status": "match",
        }
        purchase_order_value = purchase_order_context(
            item_code=item_code,
            sales_order=None,
            po_line=None,
        )

        for order in item.get("sales_orders", []):
            sales_order_raw = order.get("sales_order")
            sales_order_10_digit = first_ten_digit_sales_order(
                sales_order_raw
            )
            sales_order_full = full_sales_order(
                sales_order_raw
            )

            if is_missing(sales_order_10_digit):
                continue

            if is_missing(customer_order_checks["sales_order"]["purchase_order"]):
                customer_order_checks["sales_order"]["purchase_order"] = (
                    sales_order_10_digit
                )

            if is_missing(
                comparison_context["individual_sales_order"]["purchase_order"]
            ):
                comparison_context["individual_sales_order"] = {
                    "work_order": work_order_sales_order_raw,
                    "purchase_order": sales_order_raw,
                    "status": exact_status(
                        work_order_sales_order_full,
                        sales_order_full,
                    ),
                }

            if sales_order_10_digit != work_order_sales_order_10_digit:
                continue

            customer_order_checks["sales_order"] = {
                "work_order": work_order_sales_order_10_digit,
                "purchase_order": sales_order_10_digit,
                "status": exact_status(
                    work_order_sales_order_10_digit,
                    sales_order_10_digit,
                ),
            }
            comparison_context["individual_sales_order"] = {
                "work_order": work_order_sales_order_raw,
                "purchase_order": sales_order_raw,
                "status": exact_status(
                    work_order_sales_order_full,
                    sales_order_full,
                ),
            }
            sizes = order.get("sizes", [])
            first_po_line = (
                str(sizes[0].get("po_line") or "").strip()
                if sizes
                else None
            )

            purchase_order_value = purchase_order_context(
                item_code=item_code,
                sales_order=sales_order_10_digit,
                po_line=first_po_line,
            )

            if not first_po_line:
                customer_order_checks["po_line"] = {
                    "work_order": work_order.get("line_item"),
                    "purchase_order": None,
                    "status": "missing",
                }

                return {
                    "field": "Customer Order Number",
                    "work_order": customer_order_no,
                    "purchase_order": purchase_order_value,
                    "booking_sheet": None,
                    "status": "missing",
                    "matched_values": customer_order_checks,
                }

            customer_order_checks["po_line"]["purchase_order"] = first_po_line

            if first_po_line == work_order_po_line:
                customer_order_checks["po_line"] = {
                    "work_order": work_order.get("line_item"),
                    "purchase_order": first_po_line,
                    "status": "match",
                }
                return {
                    "field": "Customer Order Number",
                    "work_order": customer_order_no,
                    "purchase_order": purchase_order_value,
                    "booking_sheet": None,
                    "status": overall_status(
                        [
                            customer_order_checks["item_code"]["status"],
                            customer_order_checks["sales_order"]["status"],
                            customer_order_checks["po_line"]["status"],
                        ]
                    ),
                    "matched_values": customer_order_checks,
                }

            customer_order_checks["po_line"]["status"] = "mismatch"

    return {
        "field": "Customer Order Number",
        "work_order": customer_order_no,
        "purchase_order": purchase_order_value,
        "booking_sheet": None,
        "status": overall_status(
            [
                customer_order_checks["item_code"]["status"],
                customer_order_checks["sales_order"]["status"],
                customer_order_checks["po_line"]["status"],
            ]
        ),
        "matched_values": customer_order_checks,
    }


# -------------------------------------------------------------------------
# Individual checks from the customer order number (item code, sales order, and PO line) 
# -------------------------------------------------------------------------

# Item Code 
#-------------------------------------
def compare_item_code(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    customer_order_data = comparison_context.get("customer_order_number", {})
    item_code_data = customer_order_data.get("item_code", {})

    return {
        "field": "Item Code",
        "work_order": item_code_data.get("work_order"),
        "purchase_order": item_code_data.get("purchase_order"),
        "booking_sheet": None,
        "status": item_code_data.get("status", "missing"),
    }


# Sales Order number (SO Number)
#-------------------------------------
def compare_sales_order(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    sales_order_data = comparison_context.get("individual_sales_order", {})

    return {
        "field": "Sales Order Number",
        "work_order": sales_order_data.get("work_order"),
        "purchase_order": sales_order_data.get("purchase_order"),
        "booking_sheet": None,
        "status": sales_order_data.get("status", "missing"),
    }


# Line Item (PO Line)
#-------------------------------------
def compare_po_line(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    customer_order_data = comparison_context.get("customer_order_number", {})
    po_line_data = customer_order_data.get("po_line", {})

    return {
        "field": "Line Item",
        "work_order": po_line_data.get("work_order"),
        "purchase_order": po_line_data.get("purchase_order"),
        "booking_sheet": None,
        "status": po_line_data.get("status", "missing"),
    }



# Product Code (reference) comparison
# -------------------------------------
def compare_product_code(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_item_code = str(work_order.get("item_code") or "").strip()

    work_order_product_code = work_order.get("product_code")
    purchase_order_item_description = None

    # Find the PO item block having the same item code.
    for item in purchase_order.get("items", []):
        purchase_order_item_code = str(item.get("item_code") or "").strip()

        if purchase_order_item_code == work_order_item_code:
            purchase_order_item_description = item.get("item_description")
            break

    status = product_code_status(work_order_product_code, purchase_order_item_description)

    comparison_context["product_code"] = {
        "item_code": work_order_item_code or None,
        "work_order": work_order_product_code,
        "purchase_order": purchase_order_item_description,
        "status": status,
    }

    return {
        "field": "Product Code",
        "work_order": work_order_product_code,
        "purchase_order": purchase_order_item_description,
        "booking_sheet": None,
        "status": status,
    }

# ---------------------------------------------------------
# VSD# comparison
# ---------------------------------------------------------
def compare_vsd(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_vsd = work_order.get("vsd")

    # The Product Code comparison already found the correct
    # PO item and stored its item_description here.
    product_code_data = comparison_context.get("product_code", {})

    purchase_order_item_description = (product_code_data.get("purchase_order"))

    status = vsd_status(work_order_vsd, purchase_order_item_description)

    comparison_context["vsd"] = {
        "work_order": work_order_vsd,
        "purchase_order": purchase_order_item_description,
        "status": status,
    }

    return {
        "field": "VSD #",
        "work_order": work_order_vsd,
        "purchase_order": purchase_order_item_description,
        "booking_sheet": None,
        "status": status,
    }


# -----------------------------------------------------------
# Factory ID comparison
# -----------------------------------------------------------
def compare_factory_id(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("factory_id")
    purchase_order_value = purchase_order.get("factory_id")

    status = exact_status(work_order_value, purchase_order_value)

    return {
        "field": "Factory ID",
        "work_order": work_order_value,
        "purchase_order": purchase_order_value,
        "booking_sheet": None,
        "status": status,
    }


# -----------------------------------------------------------
# Date of Manufacturing(MFR) comparison
# -----------------------------------------------------------
def compare_date_of_mfr(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("date_of_mfr")
    purchase_order_value = purchase_order.get("date_of_mfr")

    status = mfr_date_status(work_order_value, purchase_order_value)

    return {
        "field": "Date of MFR",
        "work_order": work_order_value,
        "purchase_order": purchase_order_value,
        "booking_sheet": None,
        "status": status,
    }



# -------------------------------------------------------------------------
# Comparison functions for all fields in the work order and purchase order
# -------------------------------------------------------------------------
def compare_all_fields(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    booking_sheets: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """
    Add each new field-comparison function to this list.

    booking_sheets is already available for future Excel comparisons.
    """

    comparison_context: dict[str, Any] = {
        "booking_sheets": booking_sheets,
    }

    return [
        compare_po_number(work_order, purchase_order, comparison_context),
        compare_customer_order_number(work_order, purchase_order, comparison_context),
        compare_item_code(work_order, purchase_order, comparison_context),
        compare_sales_order(work_order, purchase_order, comparison_context),
        compare_po_line(work_order, purchase_order, comparison_context),
        compare_product_code(work_order, purchase_order, comparison_context),
        compare_vsd(work_order, purchase_order, comparison_context),
        compare_factory_id(work_order, purchase_order, comparison_context),
        compare_date_of_mfr(work_order, purchase_order, comparison_context),
    ]


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
            rows = compare_all_fields(
                work_order=work_order,
                purchase_order=purchase_order,
                booking_sheets=booking_sheets,
            )
            statuses = [row["status"] for row in rows]
            all_statuses.extend(statuses)

            work_order_results.append(
                {
                    "work_order_no": (
                        work_order.get("work_order_no")
                        or Path(source_file).stem
                    ),
                    "source_file": source_file,
                    "status": overall_status(statuses),
                    "rows": rows,
                }
            )

    counts = Counter(all_statuses)

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
            "matched": counts["match"],
            "mismatched": counts["mismatch"],
            "missing": counts["missing"],
            "review": counts["review"],
        },
        "work_orders": work_order_results,
    }
