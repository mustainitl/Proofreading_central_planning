"""Simple field-by-field comparisons for the three extracted datasets."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from backend.comparison_helpers import (
    country_of_origin_status,
    exact_status,
    first_ten_digit_sales_order,
    full_sales_order,
    is_missing,
    mfr_date_status,
    normalized_exact_status,
    overall_status,
    product_code_status,
    purchase_order_context,
    silhouette_status,
    size_id_status,
    additional_instructions_status,
    vsd_status,
    care_instructions_set_status,
    garment_components_status,
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


# -----------------------------------------------------------
# Care Instructions Set comparison
# -----------------------------------------------------------
def compare_care_instructions_set(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("care_instructions_set_1")

    # Product Code comparison already found the correct
    # PO item and stored its item_description.
    product_code_data = comparison_context.get("product_code",{})

    purchase_order_value = product_code_data.get("purchase_order")

    status = care_instructions_set_status(
        work_order_value,
        purchase_order_value,
    )

    return {
        "field": "Care Instructions Set",
        "work_order": work_order_value,
        "purchase_order": purchase_order_value,
        "booking_sheet": None,
        "status": status,
    }


# -----------------------------------------------------------
# Country of Origin comparison
# -----------------------------------------------------------
def compare_country_of_origin(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("country_of_origin")

    return {
        "field": "Country of Origin",
        "work_order": work_order_value,
        "purchase_order": None,
        "booking_sheet": None,
        "status": country_of_origin_status(work_order_value),
    }



# -----------------------------------------------------------
# Silhouette comparison
# -----------------------------------------------------------
def compare_silhouette(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("silhouette")

    booking_sheets = comparison_context.get(
        "booking_sheets",
        {},
    )

    matched_booking_rows = []
    available_booking_values = []

    for file_name, booking_rows in booking_sheets.items():
        for row_index, booking_row in enumerate(booking_rows):
            booking_sheet_value = booking_row.get(
                "Seasonless - Silhouette Code"
            )

            if is_missing(booking_sheet_value):
                continue

            available_booking_values.append(
                booking_sheet_value
            )

            status = silhouette_status(
                work_order_value,
                booking_sheet_value,
            )

            if status == "match":
                matched_booking_rows.append(
                    {
                        "source_file": file_name,
                        "row_index": row_index,
                        "data": booking_row,
                    }
                )

    # Save all matched rows because future Size ID and
    # Garment Component checks must use these same rows.
    comparison_context["matched_booking_rows"] = (
        matched_booking_rows
    )

    if is_missing(work_order_value):
        booking_sheet_value = None
        status = "missing"

    elif matched_booking_rows:
        booking_sheet_value = matched_booking_rows[0][
            "data"
        ].get("Seasonless - Silhouette Code")

        status = "match"

    elif available_booking_values:
        unique_booking_values = list(
            dict.fromkeys(available_booking_values)
        )

        booking_sheet_value = "\n".join(
            str(value)
            for value in unique_booking_values
        )

        status = "mismatch"

    else:
        booking_sheet_value = None
        status = "missing"

    comparison_context["silhouette"] = {
        "work_order": work_order_value,
        "booking_sheet": booking_sheet_value,
        "status": status,
    }

    return {
        "field": "Silhouette",
        "work_order": work_order_value,
        "purchase_order": None,
        "booking_sheet": booking_sheet_value,
        "status": status,
    }



# -----------------------------------------------------------
# Size ID comparison
# -----------------------------------------------------------
def compare_size_id(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get("size_id")

    # These rows were selected by compare_silhouette().
    silhouette_booking_rows = comparison_context.get(
        "matched_booking_rows",
        [],
    )

    matched_size_id_rows = []
    available_booking_values = []

    for matched_booking in silhouette_booking_rows:
        booking_row = matched_booking.get("data", {})

        booking_sheet_value = booking_row.get(
            "Seasonless - Product Content Summary"
        )

        if is_missing(booking_sheet_value):
            continue

        available_booking_values.append(
            booking_sheet_value
        )

        status = size_id_status(
            work_order_value,
            booking_sheet_value,
        )

        if status == "match":
            matched_size_id_rows.append(
                matched_booking
            )

    # Save these narrowed rows for the future Garment
    # Components and Fabric Components comparisons.
    comparison_context["matched_size_id_booking_rows"] = (
        matched_size_id_rows
    )

    if is_missing(work_order_value):
        booking_sheet_value = None
        status = "missing"

    elif matched_size_id_rows:
        booking_sheet_value = matched_size_id_rows[0][
            "data"
        ].get("Seasonless - Product Content Summary")

        status = "match"

    elif available_booking_values:
        booking_sheet_value = available_booking_values[0]
        status = "mismatch"

    else:
        booking_sheet_value = None
        status = "missing"

    comparison_context["size_id"] = {
        "work_order": work_order_value,
        "booking_sheet": booking_sheet_value,
        "status": status,
    }

    return {
        "field": "Size ID",
        "work_order": work_order_value,
        "purchase_order": None,
        "booking_sheet": booking_sheet_value,
        "status": status,
    }


# -----------------------------------------------------------
# Additional Instructions comparison
# -----------------------------------------------------------
def compare_additional_instructions(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get(
        "additional_instructions"
    )

    # Use booking rows already matched by Silhouette and Size ID.
    matched_booking_rows = comparison_context.get(
        "matched_size_id_booking_rows",
        [],
    )

    booking_sheet_value = None
    status = (
        "missing"
        if is_missing(work_order_value)
        else "missing"
    )

    for matched_booking in matched_booking_rows:
        booking_row = matched_booking.get("data", {})

        current_booking_value = booking_row.get(
            "Seasonless - Product Content Summary"
        )

        if is_missing(current_booking_value):
            continue

        # Keep the first available value for mismatch display.
        if booking_sheet_value is None:
            booking_sheet_value = current_booking_value
            status = "mismatch"

        current_status = additional_instructions_status(
            work_order_value,
            current_booking_value,
        )

        if current_status == "match":
            booking_sheet_value = current_booking_value
            status = "match"
            break

    return {
        "field": "Additional Instructions",
        "work_order": work_order_value,
        "purchase_order": None,
        "booking_sheet": booking_sheet_value,
        "status": status,
    }



# -----------------------------------------------------------
# Garment Components comparison
# -----------------------------------------------------------
def compare_garment_components(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> dict[str, Any]:
    work_order_value = work_order.get(
        "garment_components"
    )

    # Prefer rows matched by both Silhouette and Size ID.
    matched_booking_rows = comparison_context.get(
        "matched_size_id_booking_rows",
        [],
    )

    # Fallback to rows matched by Silhouette.
    if not matched_booking_rows:
        matched_booking_rows = comparison_context.get(
            "matched_booking_rows",
            [],
        )

    booking_sheet_value = None
    final_status = "missing"
    final_message = None

    for matched_booking in matched_booking_rows:
        booking_row = matched_booking.get("data", {})

        current_booking_value = booking_row.get(
            "Seasonless - Product Content Summary"
        )

        current_status, current_message = (
            garment_components_status(
                work_order_value,
                current_booking_value,
            )
        )

        # Keep the first booking value for mismatch display.
        if booking_sheet_value is None:
            booking_sheet_value = current_booking_value
            final_status = current_status
            final_message = current_message

        if current_status == "match":
            booking_sheet_value = current_booking_value
            final_status = "match"
            final_message = None
            break

    # Validate the Work Order total even when no booking
    # row was selected.
    if not matched_booking_rows:
        final_status, final_message = (
            garment_components_status(
                work_order_value,
                None,
            )
        )

    return {
        "field": "Garment Components",
        "work_order": work_order_value,
        "purchase_order": None,
        "booking_sheet": booking_sheet_value,
        "status": final_status,
        "message": final_message,
    }


#-----------------------------------------------------------
# Size/Age Breakdown comparison
#-----------------------------------------------------------
def compare_size_age_breakdown(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    comparison_context: dict[str, Any],
) -> list[dict[str, Any]]:
    work_order_item_code = str(
        work_order.get("item_code") or ""
    ).strip()

    work_order_sales_order = full_sales_order(work_order.get("so_number"))

    work_order_po_line = work_order.get("line_item")
    work_order_size_rows = (work_order.get("size_age_breakdown") or [])

    matched_sales_order = None

    # Find the correct item block.
    for item in purchase_order.get("items") or []:
        purchase_order_item_code = str(item.get("item_code") or "").strip()

        if purchase_order_item_code != work_order_item_code:
            continue

        # Find the correct sales-order block.
        for sales_order_data in item.get("sales_orders") or []:
            purchase_order_sales_order = full_sales_order(sales_order_data.get("sales_order"))

            if (purchase_order_sales_order == work_order_sales_order):
                matched_sales_order = sales_order_data
                break

        if matched_sales_order is not None:
            break

    purchase_order_sizes = (matched_sales_order.get("sizes") or [] if matched_sales_order else [])

    purchase_order_sizes_by_name = {
        str(size_data.get("size") or "").strip().upper(): size_data
        for size_data in purchase_order_sizes
        if not is_missing(size_data.get("size"))
    }

    size_rows = []

    for work_order_size_data in work_order_size_rows:
        size_field = next(
            (
                key
                for key in work_order_size_data
                if key not in {"Line No", "Order Quantity"}
            ),
            None,
        )

        work_order_full_size = (
            work_order_size_data.get(size_field)
            if size_field
            else None
        )

        # "L | G | 170/80A" becomes "L" for matching.
        work_order_primary_size = (
            str(work_order_full_size)
            .split("|", 1)[0]
            .strip()
            .upper()
            if not is_missing(work_order_full_size)
            else None
        )

        work_order_quantity = work_order_size_data.get("Order Quantity")

        purchase_order_size_data = (purchase_order_sizes_by_name.get(work_order_primary_size, {}, ))

        purchase_order_size = purchase_order_size_data.get("size")
        purchase_order_po_line = purchase_order_size_data.get("po_line")
        purchase_order_quantity = purchase_order_size_data.get("quantity")

        size_status = normalized_exact_status(work_order_primary_size, purchase_order_size)
        po_line_status = normalized_exact_status(work_order_po_line, purchase_order_po_line)
        quantity_status = normalized_exact_status(work_order_quantity, purchase_order_quantity)

        status = overall_status([size_status, po_line_status, quantity_status])

        work_order_display = (
            f"Size: {work_order_full_size or '-'}\n"
            f"PO Line: {work_order_po_line or '-'}\n"
            f"Quantity: {work_order_quantity or '-'}"
        )

        purchase_order_display = (
            f"Size: {purchase_order_size or '-'}\n"
            f"PO Line: {purchase_order_po_line or '-'}\n"
            f"Quantity: "
            f"{purchase_order_quantity if purchase_order_quantity is not None else '-'}"
        )

        size_rows.append(
            {
                "field": (
                    f"{size_field or 'Size'} "
                    f"({work_order_primary_size or 'Unknown'})"
                ),
                "work_order": work_order_display,
                "purchase_order": purchase_order_display,
                "booking_sheet": None,
                "status": status,
            }
        )

    return size_rows




# -------------------------------------------------------------------------
# Comparison functions for all fields in the work order and purchase order
# -------------------------------------------------------------------------
def compare_all_fields(
    work_order: dict[str, Any],
    purchase_order: dict[str, Any],
    booking_sheets: dict[str, list[dict[str, Any]]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    """
    Add each new field-comparison function to this list.

    booking_sheets is already available for future Excel comparisons.
    """

    comparison_context: dict[str, Any] = {
        "booking_sheets": booking_sheets,
    }

    rows = [
        compare_po_number(work_order, purchase_order, comparison_context),
        compare_customer_order_number(work_order, purchase_order, comparison_context),
        compare_item_code(work_order, purchase_order, comparison_context),
        compare_sales_order(work_order, purchase_order, comparison_context),
        compare_po_line(work_order, purchase_order, comparison_context),
        compare_product_code(work_order, purchase_order, comparison_context),
        compare_vsd(work_order, purchase_order, comparison_context),
        compare_factory_id(work_order, purchase_order, comparison_context),
        compare_date_of_mfr(work_order, purchase_order, comparison_context),
        compare_care_instructions_set(work_order, purchase_order, comparison_context),
        compare_country_of_origin(work_order, purchase_order, comparison_context),
        compare_silhouette(work_order, purchase_order, comparison_context),
        compare_size_id(work_order, purchase_order, comparison_context),
        compare_additional_instructions(work_order, purchase_order, comparison_context),
        compare_garment_components(work_order, purchase_order, comparison_context),
    ]

    size_rows = compare_size_age_breakdown(work_order, purchase_order, comparison_context)


    # Keep booking_sheets in the real context, but do not print
    # its potentially large extracted data.
    printable_context = {
        key: value
        for key, value in comparison_context.items()
        if key != "booking_sheets"
    }

    print(
        f"\nCOMPARISON CONTEXT FOR WORK ORDER: "
        f"{work_order.get('work_order_no', 'Unknown')}"
    )

    print(
        json.dumps(
            printable_context,
            indent=4,
            ensure_ascii=False,
            default=str,
        )
    )

    return rows, size_rows


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
            rows, size_rows = compare_all_fields(
                work_order=work_order,
                purchase_order=purchase_order,
                booking_sheets=booking_sheets,
            )

            statuses = [
                row["status"]
                for row in [*rows, *size_rows]
            ]
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
                    "size_rows": size_rows,
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
