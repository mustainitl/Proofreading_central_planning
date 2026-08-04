import json
import re
import sys
from pathlib import Path

import pdfplumber


def clean_cell(value):
    return " ".join((value or "").split()).strip()


def clean_value(value):
    return " ".join((value or "").split()).strip()


def is_number(value):
    return clean_cell(value).replace(",", "").isdigit()


def clean_garment_components(value):
    value = value.replace("&", "")
    value = value.replace("Fibre Contents:", "")
    value = " ".join(value.split())
    return value.strip()


def clean_page_text(value):
    cleaned_lines = []

    for raw_line in (value or "").splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if "International Trimmings & Labels Plc - Order Form" in line:
            continue

        if "labelvantage.itl-group.com" in line:
            continue

        if re.match(r"^\d+\s+of\s+\d+\b", line, flags=re.IGNORECASE):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_pdf_once(pdf_path):
    document_pages = []
    extracted_texts = []
    size_age_rows = []

    size_header = None
    collecting_size = False

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = clean_page_text(page.extract_text() or "")

            if page_text:
                document_pages.append(page_text)

            for table in page.extract_tables():
                for row in table:
                    row_start_pos = len(extracted_texts)
                    cells = [clean_cell(cell) for cell in row]

                    for cell in cells:
                        if cell:
                            extracted_texts.append(cell)

                    if not any(cells):
                        continue

                    if cells[-1] == "Order Quantity":
                        size_header = cells
                        collecting_size = True
                        continue

                    if not collecting_size or size_header is None:
                        continue

                    if cells == size_header:
                        continue

                    if len(cells) != len(size_header):
                        continue

                    if not is_number(cells[-1]):
                        continue

                    size_age_rows.append(
                        {
                            "position": row_start_pos,
                            "data": dict(zip(size_header, cells)),
                        }
                    )

    document_text = "\n".join(document_pages)
    return document_text, extracted_texts, size_age_rows


def split_table_work_orders(extracted_texts):
    work_orders = []
    start_pos = 0
    index = 0

    while index < len(extracted_texts) - 1:
        current_item = extracted_texts[index]
        next_item = extracted_texts[index + 1]

        if "End of Works Order:" not in current_item:
            index += 1
            continue

        work_order_match = re.search(r"\*([^*]+)\*", next_item)

        if not work_order_match:
            index += 1
            continue

        work_order_no = work_order_match.group(1).strip()
        block_items = extracted_texts[start_pos:index + 2]
        block_text = "\n".join(block_items)

        work_orders.append(
            {
                "work_order_no": work_order_no,
                "work_order_exists_in_block": work_order_no in block_text,
                "start_pos": start_pos,
                "end_pos": index + 1,
                "items": block_items,
            }
        )

        start_pos = index + 2
        index = start_pos

    return work_orders


def split_text_work_orders(document_text):
    work_orders = []
    start_pos = 0

    end_pattern = re.compile(
        r"End of Works(?:"
        r"\s+Order:\s*\*([^*]+)\*"
        r"|"
        r"\s*\*([^*]+)\*\s*Order:"
        r")",
        flags=re.IGNORECASE,
    )

    for match in end_pattern.finditer(document_text):
        work_order_no = next(
            group.strip()
            for group in match.groups()
            if group
        )
        block_text = document_text[start_pos:match.end()]

        work_orders.append(
            {
                "work_order_no": work_order_no,
                "work_order_exists_in_block": work_order_no in block_text,
                "text": block_text,
            }
        )

        start_pos = match.end()

    return work_orders


def extract_size_age_breakdown_from_text(block_text):
    section_match = re.search(
        (
            r"Size/Age Breakdown:\s*(.*?)"
            r"(?=\n(?:ITL Factory Code|Number of Size|VSD#|VSS#|RN#|"
            r"CA#|Factory ID|Date of MFR#|Country Of Origin|"
            r"Additional Instructions|Garment Components|Care Instructions))"
        ),
        block_text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not section_match:
        return []

    lines = [
        line.strip()
        for line in section_match.group(1).splitlines()
        if line.strip()
    ]

    size_header = None
    size_rows = []

    for line in lines:
        if "Line No" in line and "Order Quantity" in line:
            size_header = re.sub(
                r"\s+Line No\s+Order Quantity\s*$",
                "",
                line,
                flags=re.IGNORECASE,
            ).strip()
            continue

        row_match = re.match(r"^(.*?)\s+(\d[\d,]*)$", line)

        if size_header and row_match:
            size_rows.append(
                {
                    size_header: row_match.group(1).strip(),
                    "Line No": "",
                    "Order Quantity": row_match.group(2).replace(",", ""),
                }
            )

    return size_rows


def find_with_patterns(text, patterns):
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.MULTILINE | re.DOTALL,
        )

        if match:
            return match

    return None


def extract_fields_independently(block_text, rules):
    """
    Every rule searches the complete current work-order block.

    There is no shared cursor, so a missing or reordered field does not
    change where the following field starts searching.
    """
    result = {}

    for rule in rules:
        key = rule["key"]
        match = find_with_patterns(block_text, rule["patterns"])

        if not match:
            result[key] = ""
            continue

        if key == "customer_order_no":
            captured_value = "".join(
                group
                for group in match.groups()
                if group
            )

            if not re.fullmatch(
                r"\d{10}-\d{10}/\d{2}-\d{10}-\d+",
                captured_value,
            ):
                result[key] = ""
                continue

            result[key] = clean_value(captured_value)
            continue

        result[key] = clean_value(match.group(1))

    return result


RULES = [
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
            (
                r"Customer Order No:\s*"
                r"(\d{10}-\d{10}/\d{2}-\d{10}-\d+)"
            ),
            (
                r"(?<![A-Za-z0-9])"
                r"([0-9][0-9/-]*)"
                r"(?![A-Za-z0-9])"
                r"\s*Customer Order No:\s*"
                r".*?"
                r"(?<![A-Za-z0-9])"
                r"([/-]*[0-9][0-9/-]*)"
                r"(?![A-Za-z0-9])"
                r"\s*(?=ITL BD PRODUCTION SPECIFICATIONS:)"
            ),
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


def extract_work_orders(pdf_path):
    document_text, extracted_texts, size_age_rows = extract_pdf_once(pdf_path)

    text_blocks = split_text_work_orders(document_text)
    table_blocks = split_table_work_orders(extracted_texts)
    size_rows_by_work_order = {}

    for table_block in table_blocks:
        work_order_no = table_block["work_order_no"]
        matching_rows = [
            row["data"]
            for row in size_age_rows
            if (
                table_block["start_pos"]
                <= row["position"]
                <= table_block["end_pos"]
            )
        ]

        if matching_rows:
            size_rows_by_work_order.setdefault(
                work_order_no,
                [],
            ).extend(matching_rows)

    all_work_orders = []

    for block in text_blocks:
        result = {
            "work_order_no": block["work_order_no"],
            "work_order_exists_in_block": block["work_order_exists_in_block"],
        }

        if not block["work_order_exists_in_block"]:
            result["error"] = "Work order number not found inside this block"
            all_work_orders.append(result)
            continue

        extracted_values = extract_fields_independently(
            block["text"],
            RULES,
        )

        if extracted_values.get("garment_components"):
            extracted_values["garment_components"] = clean_garment_components(
                extracted_values["garment_components"]
            )

        result.update(extracted_values)

        result["size_age_breakdown"] = (
            size_rows_by_work_order.get(block["work_order_no"])
            or extract_size_age_breakdown_from_text(block["text"])
        )

        all_work_orders.append(result)

    return all_work_orders


def main():
    vs_directory = Path(__file__).resolve().parent.parent

    pdf_paths = [
        vs_directory / "input_files" / "BD01529397W_workorder.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01425038W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01425042W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01425044W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01538728W_work_order.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01538742W_work_order.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01538806W_work_order.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01550748W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01550768W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01550770W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01556226W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01556227W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01556235W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01468527W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01468626W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01470623W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01470631W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01468543W.pdf",
        vs_directory / "input_files" / "work_orders" / "BD01470576W.pdf",
    ]

    output = {}

    for pdf_path in pdf_paths:
        if not pdf_path.exists():
            output[pdf_path.name] = {
                "error": f"PDF file not found: {pdf_path}"
            }
            continue

        output[pdf_path.name] = extract_work_orders(pdf_path)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(json.dumps(output, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()
