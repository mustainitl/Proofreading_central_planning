import json
import sys
from pathlib import Path

import pandas as pd


INPUT_DIRECTORY = Path(__file__).resolve().parent.parent / "input_files/bookings"

COLUMNS_TO_EXTRACT = [
    "Seasonless - Silhouette Code",
    "Seasonless - Product Content Summary",
]

EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}


def extract_columns(excel_path):
    df = pd.read_excel(excel_path)

    missing_columns = [
        column
        for column in COLUMNS_TO_EXTRACT
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in {excel_path.name}: {missing_columns}"
        )

    df = df[COLUMNS_TO_EXTRACT]
    df = df.dropna()

    return df.to_dict(orient="records")


def extract_all_excel_files(input_directory):
    result = {}

    excel_files = sorted(
        file_path
        for file_path in input_directory.iterdir()
        if file_path.is_file()
        and file_path.suffix.lower() in EXCEL_EXTENSIONS
        and not file_path.name.startswith("~$")
    )

    if not excel_files:
        raise FileNotFoundError(
            f"No Excel files found in: {input_directory}"
        )

    for excel_path in excel_files:
        result[excel_path.stem] = extract_columns(excel_path)

    return result


def main():
    result = extract_all_excel_files(INPUT_DIRECTORY)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, indent=4, ensure_ascii=False))
 
   
if __name__ == "__main__":
    main()
    
