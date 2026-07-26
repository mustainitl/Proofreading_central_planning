import re
from itertools import combinations
import pdfplumber
from pathlib import Path
import json


# PDF_PATH = r"../input_files/4502859819.pdf"
# PDF_PATH = Path(r"C:/Users/N_R_KHAN/Documents/ITL_PROJECTS/Proofreading_central_planning/VS/input_files/po/4502903587.pdf")
# PDF_PATH = Path(r"C:/Users/N_R_KHAN/Documents/ITL_PROJECTS/Proofreading_central_planning/VS/input_files/po/4502903592.pdf")
# PDF_PATH = Path(r"C:/Users/N_R_KHAN/Documents/ITL_PROJECTS/Proofreading_central_planning/VS/input_files/po/4502914965.pdf")
# PDF_PATH = Path(r"C:/Users/N_R_KHAN/Documents/ITL_PROJECTS/Proofreading_central_planning/VS/input_files/po/4502914995.pdf")
# PDF_PATH = Path(r"C:/Users/N_R_KHAN/Documents/ITL_PROJECTS/Proofreading_central_planning/VS/input_files/po/4502915150.pdf")
PDF_PATH = Path(r"C:/Users/N_R_KHAN/Documents/ITL_PROJECTS/Proofreading_central_planning/VS/input_files/po/4502916826.pdf")


def find_boxes(page, tolerance=4):
    horizontal = [
        e for e in page.edges
        if e["orientation"] == "h" and e["width"] > 120
    ]
    vertical = [
        e for e in page.edges
        if e["orientation"] == "v" and e["height"] > 80
    ]

    boxes = set()

    for first, second in combinations(horizontal, 2):
        top, bottom = sorted((first, second), key=lambda e: e["top"])

        # Prevent zero-height or very small boxes.
        if bottom["top"] - top["top"] < 20:
            continue

        if (
            abs(top["x0"] - bottom["x0"]) > tolerance
            or abs(top["x1"] - bottom["x1"]) > tolerance
        ):
            continue

        left_exists = any(
            abs(v["x0"] - top["x0"]) <= tolerance
            and v["top"] <= top["top"] + tolerance
            and v["bottom"] >= bottom["top"] - tolerance
            for v in vertical
        )

        right_exists = any(
            abs(v["x0"] - top["x1"]) <= tolerance
            and v["top"] <= top["top"] + tolerance
            and v["bottom"] >= bottom["top"] - tolerance
            for v in vertical
        )

        if left_exists and right_exists:
            box = (
                round(top["x0"], 2),
                round(top["top"], 2),
                round(top["x1"], 2),
                round(bottom["top"], 2),
            )
            boxes.add(box)

    return list(boxes)


def extract_po_details(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[0]

        box_texts = [
            page.crop(box).extract_text() or ""
            for box in find_boxes(page)
        ]

    # Find the Purchase Order box.
    po_box = next(
        text for text in box_texts
        if "Purchase Order" in text and "PO Number" in text
    )

    # Find the Payment Term box.
    payment_box = next(
        text for text in box_texts
        if "Payment Term" in text
    )

    po_match = re.search(
        r"PO\s*Number\s*(\d{10})",
        po_box,
        re.IGNORECASE,
    )

    factory_match = re.search(
        r"\b\d{8}\b",
        payment_box,
    )

    date_match = re.search(
        r"\b\d{1,4}[/-]\d{1,4}\b",
        payment_box,
    )

    po_number = po_match.group(1) if po_match else None
    factory_id = factory_match.group(0) if factory_match else None
    date_of_mfr = date_match.group(0) if date_match else None

    result = {
        "po_number": po_number,
        "factory_id": factory_id,
        "date_of_mfr": date_of_mfr,
    }

    return result


def extract_clean_text(pdf_path):
    all_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n"

    m = re.search(r"LINE#.*?\n(.*?)\nREMARKS", all_text, re.S)

    if m:
        extracted = m.group(1).strip()
    else:
        raise ValueError("No LINE# to REMARKS section found.")

    lines = extracted.splitlines()

    po_numbers = []

    for line in lines:
        po_match = re.search(
            r"PO\s*Number\s*-\s*(\d{10})",
            line,
            re.IGNORECASE,
        )
        if po_match:
            po_numbers.append(po_match.group(1))

    if po_numbers and len(set(po_numbers)) == 1:
        po_number = po_numbers[0]
    else:
        raise ValueError(f"PO number is not same for all pages: {po_numbers}")

    remove_starts = (
        "Acceptance of this order",
        "PO SALES ORDER",
        "LINE#",
    )

    clean_lines = [
        line for line in lines
        if line.strip()
        and not line.lstrip().startswith(remove_starts)
        and not re.search(r"PO\s*Number\s*-\s*\d{10}", line, re.IGNORECASE)
    ]

    clean_text = "\n".join(clean_lines)
    return clean_text


def extract_items(clean_text):
    item_pattern = re.compile(
        r"^(\d{10})\s+([A-Z].*?)\s+\d[\d,]*\.\d+\s+PC\b"
    )

    sales_order_pattern = re.compile(
        r"^(\d{10})\s*/\s*(\d+)\s*$"
    )

    size_pattern = re.compile(
        r"^(\d+)\s+(\S+)\s+([\d,]+(?:\.\d+)?)\s+PC\b"
    )

    items = []
    current_item = None
    current_order = None

    for line in clean_text.splitlines():
        line = line.strip()

        # New item
        match = item_pattern.search(line)

        if match:
            current_item = {
                "item_code": match.group(1),
                "item_description": match.group(2),
                "sales_orders": []
            }

            items.append(current_item)
            current_order = None
            continue

        # New sales order
        match = sales_order_pattern.search(line)

        if match and current_item:
            current_order = {
                "sales_order": f"{match.group(1)} / {match.group(2)}",
                "sizes": []
            }

            current_item["sales_orders"].append(current_order)
            continue

        # Size and quantity row
        match = size_pattern.search(line)

        if match and current_order:
            quantity = float(match.group(3).replace(",", ""))

            if quantity.is_integer():
                quantity = int(quantity)

            current_order["sizes"].append({
                "po_line": match.group(1),
                "size": match.group(2),
                "quantity": quantity
            })
            continue

        # Additional item-description line
        if current_item and not current_item["sales_orders"]:
            current_item["item_description"] += " " + line

    return items


def main():
    result = extract_po_details(PDF_PATH)
    clean_text = extract_clean_text(PDF_PATH)
    result["items"] = extract_items(clean_text)
    print(json.dumps(result, indent=4))


if __name__ == "__main__":
    main()
