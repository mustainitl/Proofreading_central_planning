"""Small helper functions used by the field comparisons.

Initially work order used to develop these logic was: BD01529397W
"""


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

    return ("match" if work_order_value == target_value else "mismatch")


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


# -----------------------------------------------------------
# Product Code(reference) comparison helpers
# -----------------------------------------------------------
# def product_code_status(
#     work_order_value: Any,
#     purchase_order_value: Any,
# ) -> str:
#     if is_missing(work_order_value) or is_missing(purchase_order_value):
#         return "missing"

#     wo_product_code = str(work_order_value).upper()
#     po_item_description = str(purchase_order_value).upper()

#     parts = {}

#     for part in wo_product_code.split():
#         if part == "/":
#             continue

#         parts[part] = list(
#             dict.fromkeys(
#                 [
#                     part,
#                     part.replace("/", ""),
#                     part.replace("-", ""),
#                     part.replace("/", "").replace("-", ""),
#                 ]
#             )
#         )

#     if not parts:
#         return "missing"

#     po_tokens = po_item_description.split()

#     is_match = all(
#         any(value in po_tokens for value in possible_values)
#         for possible_values in parts.values()
#     )

#     return "match" if is_match else "mismatch"

def product_code_status(
    work_order_value,
    purchase_order_value,
):
    if is_missing(work_order_value) or is_missing(purchase_order_value):
        return "missing"

    wo_product_code = str(work_order_value).upper()
    po_item_description = str(purchase_order_value).upper()

    wo_parts = {}

    for part in wo_product_code.split():
        if part == "/":
            continue

        wo_parts[part] = list(
            dict.fromkeys(
                [
                    part,
                    part.replace("/", ""),
                    part.replace("-", ""),
                    part.replace("/", "").replace("-", ""),
                ]
            )
        )

    if not wo_parts:
        return "missing"

    po_parts = {}

    for part in re.split(r"[\s-]+", po_item_description):
        if not part or part == "/":
            continue

        po_parts[part] = list(
            dict.fromkeys(
                [
                    part,
                    part.replace("/", ""),
                    part.replace("-", ""),
                    part.replace("/", "").replace("-", ""),
                ]
            )
        )

    po_tokens = {
        value
        for possible_values in po_parts.values()
        for value in possible_values
    }

    print("WO Parts:", wo_parts)
    print("PO Parts:", po_parts)
    print("PO Tokens:", po_tokens)

    for part, possible_values in wo_parts.items():
        print(f"\nChecking: {part}")
        print("Possible values:", possible_values)
        print(
            "Matched:",
            [
                value
                for value in possible_values
                if value in po_tokens
            ],
        )

    is_match = all(
        any(
            value in po_tokens
            for value in possible_values
        )
        for possible_values in wo_parts.values()
    )

    print("\nFinal Result:", is_match)

    return "match" if is_match else "mismatch"




# -----------------------------------------------------------
# VSD comparison helpers
# -----------------------------------------------------------
def vsd_status(
    work_order_vsd: Any,
    purchase_order_item_description: Any,
) -> str:
    if (is_missing(work_order_vsd) or is_missing(purchase_order_item_description)):
        return "missing"

    normalized_work_order_vsd = (
        str(work_order_vsd)
        .upper()
        .replace(" ", "")
        .replace("-", "")
        .replace("/", "")
    )

    purchase_order_tokens = (
        str(purchase_order_item_description)
        .upper()
        .split()
    )

    normalized_purchase_order_tokens = [
        token
        .replace("-", "")
        .replace("/", "")
        for token in purchase_order_tokens
        if token != "/"
    ]

    print("Normalized Work Order VSD:", normalized_work_order_vsd)
    print("Normalized PO Tokens:", normalized_purchase_order_tokens)

    # is_match = (normalized_work_order_vsd in normalized_purchase_order_tokens)
    is_match = any(normalized_work_order_vsd in text for text in normalized_purchase_order_tokens)

    return "match" if is_match else "mismatch"


# -----------------------------------------------------------
# MFR Date comparison helpers
# -----------------------------------------------------------
def normalize_mfr_date(value: Any) -> str | None:
    if is_missing(value):
        return None

    date_parts = re.findall(r"\d+", str(value))

    if len(date_parts) != 2:
        return None

    first_part = date_parts[0]
    second_part = date_parts[1]

    # Format: YYYY/MM
    if len(first_part) == 4:
        year = int(first_part)
        month = int(second_part)

    # Format: MM/YYYY
    elif len(second_part) == 4:
        month = int(first_part)
        year = int(second_part)

    # Format: MM/YY or MM YY
    else:
        month = int(first_part)
        year = 2000 + int(second_part)

    if month < 1 or month > 12:
        return None

    return f"{year:04d}-{month:02d}"


def mfr_date_status(
    work_order_value: Any,
    purchase_order_value: Any,
) -> str:
    if (is_missing(work_order_value) or is_missing(purchase_order_value)):
        return "missing"

    normalized_work_order_date = normalize_mfr_date(work_order_value)
    normalized_purchase_order_date = normalize_mfr_date(purchase_order_value)

    if (normalized_work_order_date is None or normalized_purchase_order_date is None):
        return "mismatch"

    return (
        "match"
        if normalized_work_order_date
        == normalized_purchase_order_date
        else "mismatch"
    )


# -----------------------------------------------------------
# Care Instructions Set comparison helpers
# -----------------------------------------------------------
def care_instructions_set_status(
    work_order_value: Any,
    purchase_order_item_description: Any,
) -> str:
    if (
        is_missing(work_order_value)
        or is_missing(purchase_order_item_description)
    ):
        return "missing"

    normalized_work_order_value = (
        str(work_order_value)
        .upper()
        .strip()
    )

    # purchase_order_tokens = (
    #     str(purchase_order_item_description)
    #     .upper()
    #     .split()
    # )
    purchase_order_tokens = re.split(r"[\s-]+", purchase_order_item_description.upper().strip())

    return (
        "match"
        if normalized_work_order_value in purchase_order_tokens
        else "mismatch"
    )



#-----------------------------------------------------------
# Country of Origin comparison helpers
#-----------------------------------------------------------

def country_of_origin_status(work_order_value: Any) -> str:
    if is_missing(work_order_value):
        return "missing"

    normalized_origins = [
        re.sub(r"[^a-z0-9]+", "", origin.casefold())
        for origin in str(work_order_value).split("/")
        if origin.strip()
    ]

    return (
        "match"
        if "madeinbangladesh" in normalized_origins
        else "mismatch"
    )


# -----------------------------------------------------------
# Silhouette comparison helpers
# -----------------------------------------------------------

def normalize_silhouette_parts(value: Any) -> set[str]:
    if is_missing(value):
        return set()

    normalized_parts = set()

    for part in str(value).split("/"):
        normalized_part = re.sub(
            r"[^a-z0-9]+",
            "",
            part.casefold(),
        )

        if normalized_part:
            normalized_parts.add(normalized_part)

    return normalized_parts


def silhouette_status(
    work_order_value: Any,
    booking_sheet_value: Any,
) -> str:
    if (
        is_missing(work_order_value)
        or is_missing(booking_sheet_value)
    ):
        return "missing"

    work_order_parts = normalize_silhouette_parts(
        work_order_value
    )
    booking_sheet_parts = normalize_silhouette_parts(
        booking_sheet_value
    )

    if not work_order_parts or not booking_sheet_parts:
        return "missing"

    # Match when at least one normalized booking silhouette
    # exists in the Work Order silhouette.
    is_match = bool(
        work_order_parts.intersection(booking_sheet_parts)
    )

    return "match" if is_match else "mismatch"



#-----------------------------------------------------------
# Size ID comparison helpers
#-----------------------------------------------------------
def size_id_status(
    work_order_size_id: Any,
    booking_sheet_product_content: Any,
) -> str:
    if (
        is_missing(work_order_size_id)
        or is_missing(booking_sheet_product_content)
    ):
        return "missing"

    work_order_text = str(work_order_size_id)

    # Remove "VSGLOBAL003 - " from:
    # "VSGLOBAL003 - Panties/Swim Bottoms"
    size_id_parts = re.split(
        r"\s+-\s+",
        work_order_text,
        maxsplit=1,
    )

    work_order_size_description = (
        size_id_parts[1]
        if len(size_id_parts) == 2
        else size_id_parts[0]
    )

    # Punctuation does not matter.
    # Word sequence still matters.
    work_order_words = re.findall(
        r"[a-z0-9]+",
        work_order_size_description.casefold(),
    )

    booking_sheet_words = re.findall(
        r"[a-z0-9]+",
        str(booking_sheet_product_content).casefold(),
    )

    if not work_order_words or not booking_sheet_words:
        return "missing"

    required_word_count = len(work_order_words)

    sequence_exists = any(
        booking_sheet_words[index:index + required_word_count]
        == work_order_words
        for index in range(
            len(booking_sheet_words)
            - required_word_count
            + 1
        )
    )

    return "match" if sequence_exists else "mismatch"




#-----------------------------------------------------------
# Additional Instructions comparison helpers
#-----------------------------------------------------------
def additional_instructions_status(
    work_order_value: Any,
    booking_sheet_value: Any,
) -> str:
    if (
        is_missing(work_order_value)
        or is_missing(booking_sheet_value)
    ):
        return "missing"

    # Take only the English instruction before the first "/".
    work_order_instruction = (
        str(work_order_value)
        .split("/", 1)[0]
    )

    normalized_work_order_instruction = " ".join(
        work_order_instruction
        .casefold()
        .split()
    )

    normalized_booking_sheet_value = " ".join(
        str(booking_sheet_value)
        .casefold()
        .split()
    )

    if not normalized_work_order_instruction:
        return "missing"

    return (
        "match"
        if normalized_work_order_instruction
        in normalized_booking_sheet_value
        else "mismatch"
    )


#-----------------------------------------------------------
# Garment Components comparison helpers
#-----------------------------------------------------------
def garment_components_status(
    work_order_value: Any,
    booking_sheet_value: Any,
) -> tuple[str, str | None]:
    if is_missing(work_order_value):
        return "missing", None

    work_order_text = str(work_order_value)

    # Read every explicit total directly from the original text.
    total_values = [
        float(total)
        for total in re.findall(
            r"(\d+(?:\.\d+)?)%\s*\(\s*total\s*\)",
            work_order_text,
            re.IGNORECASE,
        )
    ]

    # A total is optional. Validate it only when it is present.
    if total_values and any(total != 100 for total in total_values):
        return (
            "mismatch",
            "Composition is not 100% matched.",
        )

    # Split before every percentage and after every ")".
    composition_parts = re.split(
        r"(?<![\d.])(?=\d+(?:\.\d+)?%)|(?<=\))",
        work_order_text,
    )

    # Remove empty values and whitespace-only values.
    composition_parts = [
        part.strip()
        for part in composition_parts
        if part.strip()
    ]

    total_pattern = re.compile(
        r"^(\d+(?:\.\d+)?)%\s*\(\s*total\s*\)$",
        re.IGNORECASE,
    )

    component_parts = []
    for part in composition_parts:
        total_match = total_pattern.fullmatch(part)

        if not total_match:
            component_parts.append(part)

    if is_missing(booking_sheet_value):
        return "missing", None

    # Take only the first translation before "/".
    component_keywords = []

    for part in component_parts:
        first_translation = (
            part.split("/", 1)[0]
            .strip()
            .rstrip(":")
            .strip()
        )

        if first_translation:
            component_keywords.append(
                first_translation
            )

    # Lowercase and remove all whitespace, including tabs.
    normalized_booking_value = re.sub(
        r"\s+",
        "",
        str(booking_sheet_value).casefold(),
    )

    missing_keywords = []

    for keyword in component_keywords:
        normalized_keyword = re.sub(
            r"\s+",
            "",
            keyword.casefold(),
        )

        if normalized_keyword not in normalized_booking_value:
            missing_keywords.append(keyword)

    if missing_keywords:
        return (
            "mismatch",
            "Missing garment components: "
            + ", ".join(missing_keywords),
        )

    return "match", None




def normalized_exact_status(
    work_order_value: Any,
    purchase_order_value: Any,
) -> str:
    if (is_missing(work_order_value) or is_missing(purchase_order_value)):
        return "missing"

    normalized_work_order_value = (str(work_order_value).strip().upper())
    normalized_purchase_order_value = (str(purchase_order_value).strip().upper())

    return ("match" if normalized_work_order_value == normalized_purchase_order_value else "mismatch")


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
