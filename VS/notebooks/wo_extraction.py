import re
import json
import pdfplumber
import sys
from pathlib import Path

PDF_PATH = Path(__file__).resolve().parent.parent / "input_files" / "BD01529397W_workorder.pdf"


# Helper functions for cleaning and validating data
def clean_cell(value):
    return " ".join((value or "").split()).strip()

def clean_value(value):
    return " ".join(value.split()).strip()

def is_number(value):
    return clean_cell(value).replace(",", "").isdigit()

def clean_garment_components(value):
    value = value.replace("&", "")
    value = value.replace("Fibre Contents:", "")
    value = " ".join(value.split())
    return value.strip()

def extract_pdf_once(pdf_path):
    extracted_texts = []
    size_age_rows = []

    size_header = None
    collecting_size = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()

            for table in tables:
                for row in table:
                    row_start_pos = len(extracted_texts)
                    cells = [clean_cell(cell) for cell in row]

                    # 1. Plain text extraction from table cells
                    for cell in cells:
                        if cell:
                            extracted_texts.append(cell)

                    if not any(cells):
                        continue

                    # 2. Detect Size/Age Breakdown header dynamically
                    if cells[-1] == "Order Quantity":
                        size_header = cells
                        collecting_size = True
                        continue

                    if not collecting_size or size_header is None:
                        continue

                    # 3. Skip repeated header if table continues on another page
                    if cells == size_header:
                        continue

                    # 4. Data row must match header length
                    if len(cells) != len(size_header):
                        continue

                    # 5. Last column must be numeric quantity
                    if not is_number(cells[-1]):
                        continue

                    size_age_rows.append({
                        "position": row_start_pos,
                        "data": dict(zip(size_header, cells)),
                    })

    return extracted_texts, size_age_rows

# Split work orders based on "End of Works Order:" and extract relevant data
def split_work_orders(extracted_texts):
    work_orders = []

    start_pos = 0
    i = 0

    while i < len(extracted_texts) - 1:
        current_item = extracted_texts[i]
        next_item = extracted_texts[i + 1]

        if "End of Works Order:" not in current_item:
            i += 1
            continue

        work_order_match = re.search(r"\*([^*]+)\*", next_item)

        if not work_order_match:
            i += 1
            continue

        work_order_no = work_order_match.group(1).strip()
        block_items = extracted_texts[start_pos:i + 2]
        block_text = "\n".join(block_items)

        work_orders.append({
            "work_order_no": work_order_no,
            "work_order_exists_in_block": work_order_no in block_text,
            "start_pos": start_pos,
            "end_pos": i + 1,
            "items": block_items,
        })

        start_pos = i + 2
        i = start_pos

    return work_orders

# Sequentially extract data based on defined rules
def find_with_patterns(text, patterns):
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
        if match:
            return match

    return None

def sequential_extract(items, rules):
    result = {}

    cursor_item = 0
    cursor_char = 0

    for rule in rules:
        key = rule["key"]
        patterns = rule["patterns"]

        found = False

        for item_index in range(cursor_item, len(items)):
            item = items[item_index]

            if item_index == cursor_item:
                start_char = cursor_char
            else:
                start_char = 0

            search_text = item[start_char:]
            match = find_with_patterns(search_text, patterns)

            if not match:
                continue

            result[key] = clean_value(match.group(1))

            cursor_item = item_index
            cursor_char = start_char + match.end()

            found = True
            break

        if not found:
            result[key] = ""

    return result


rules = [
    {
        "key": "customer",
        "patterns": [
            r"Customer:\s*(.*?)\s*\[[A-Z0-9]+\]",
            r"Customer:\s*(.+)",
        ],
    },
    {
        "key": "customer_order_no",
        "patterns": [
            r"Customer Order No:\s*([0-9/-]+)",
        ],
    },
    {
        "key": "vs_po_number",
        "patterns": [
            r"VS PO Number:\s*([0-9]{10})",
        ],
    },
    {
        "key": "line_item",
        "patterns": [
            r"Line Item:\s*([0-9]+)",
        ],
    },
    {
        "key": "so_number",
        "patterns": [
            r"SO Number:\s*(\d{10}/\d{2})",
        ],
    },
    {
        "key": "item_code",
        "patterns": [
            r"Item Code:\s*([0-9]{10})",
        ],
    },
    {
        "key": "product_code",
        "patterns": [
            r"Product Code:\s*(.*?)(?=\s*Product Description:|\Z)",
        ],
    },
    {
        "key": "silhouette",
        "patterns": [
            r"Silhouette:\s*([A-Za-z/]+)",
        ],
    },
    {
        "key": "quantity",
        "patterns": [
            r"Quantity:\s*([0-9]+)\s+units",
        ],
    },
    {
        "key": "size_id",
        "patterns": [
            r"Size ID:\s*(.*?)(?:\n|Size/Age Breakdown:|\Z)",
        ],
    },
    {
        "key": "itl_factory_code",
        "patterns": [
            r"ITL Factory Code:\s*([A-Z][0-9-]+)",
        ],
    },
    {
        "key": "vsd",
        "patterns": [
            r"VSD#:\s*(\d{6}-[A-Z]{3})",
        ],
    },
    {
        "key": "vss",
        "patterns": [
            r"VSS#:\s*(\d{8})",
        ],
    },
    {
        "key": "rn",
        "patterns": [
            r"RN#:\s*(\d+)",
        ],
    },
    {
        "key": "ca",
        "patterns": [
            r"CA#:\s*(\d+)",
        ],
    },
    {
        "key": "factory_id",
        "patterns": [
            r"Factory ID:\s*(\d+)",
        ],
    },
    {
        "key": "date_of_mfr",
        "patterns": [
            r"Date of MFR#:\s*(\d{2}\s+\d{2})",
        ],
    },
    {
        "key": "country_of_origin",
        "patterns": [
            r"Country Of Origin\s*(.*?)(?=\s*Additional Instructions:|\Z)",
        ],
    },
    {
        "key": "additional_instructions",
        "patterns": [
            r"Additional Instructions:\s*(.*?)(?=\s*Garment Components|\Z)",
        ],
    },
    {
        "key": "garment_components",
        "patterns": [
            r"Garment Components\s*(.*?)(?=\s*Care Instructions:|\Z)",
        ],
    },
    {
        "key": "care_instructions_set_1",
        "patterns": [
            r"Care Instruction Set 1:\s*([A-Z0-9]+)",
        ],
    },
]



"body",
"57% cotton",
"38% modal",
"5% elastane",
"elastic",
"48% polyamide",
"37% polyester",
"15% elastane",


def extract_work_orders(pdf_path):
    # Run full extraction process
    extracted_texts, size_age_rows = extract_pdf_once(pdf_path)

    work_order_blocks = split_work_orders(extracted_texts)

    all_work_orders = []

    for block in work_order_blocks:
        result = {
            "work_order_no": block["work_order_no"],
            "work_order_exists_in_block": block["work_order_exists_in_block"],
        }

        if block["work_order_exists_in_block"]:
            extracted_values = sequential_extract(block["items"], rules)

            if extracted_values.get("garment_components"):
                extracted_values["garment_components"] = clean_garment_components(
                    extracted_values["garment_components"]
                )

            result.update(extracted_values)

            result["size_age_breakdown"] = [
                row["data"]
                for row in size_age_rows
                if block["start_pos"] <= row["position"] <= block["end_pos"]
            ]

        else:
            result["error"] = "Work order number not found inside this block"

        all_work_orders.append(result)

    return all_work_orders


def main():
    result = extract_work_orders(PDF_PATH)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()








