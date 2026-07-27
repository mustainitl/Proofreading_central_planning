from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Any
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.comparison import build_comparison_response
from VS.notebooks.booking_excel_extraction import extract_columns
from VS.notebooks.po_extraction import (
    extract_clean_text,
    extract_items,
    extract_po_details,
)
from VS.notebooks.wo_extraction import extract_work_orders


app = FastAPI(
    title="Proofreading Central Planning API",
    description=(
        "Extract information from work orders, purchase orders, "
        "and booking Excel files."
    ),
    version="1.0.0",
)


PDF_EXTENSIONS = {".pdf"}
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm"}

# Maximum size allowed for one uploaded file.
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

# Maximum files allowed in one multi-file request.
MAX_FILES_PER_REQUEST = 20

# Files are copied in chunks instead of loading the entire file into memory.
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


def get_safe_filename(upload: UploadFile) -> str:
    """
    Return only the filename, removing any directory information.
    """

    raw_filename = upload.filename or ""

    # Handle filenames sent with either Windows or Unix path separators.
    raw_filename = raw_filename.replace("\\", "/")
    filename = Path(raw_filename).name

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="An uploaded file does not have a valid filename.",
        )

    return filename


def validate_extension(
    filename: str,
    allowed_extensions: set[str],
) -> str:
    """
    Validate the file extension and return it in lowercase.
    """

    extension = Path(filename).suffix.lower()

    if extension not in allowed_extensions:
        allowed = ", ".join(sorted(allowed_extensions))

        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type for '{filename}'. "
                f"Allowed extensions: {allowed}"
            ),
        )

    return extension


def save_uploaded_file(
    upload: UploadFile,
    temporary_directory: Path,
    allowed_extensions: set[str],
) -> tuple[Path, str]:
    """
    Save an uploaded file into a temporary directory.

    Returns:
        temporary_file_path
        filename_without_extension
    """

    filename = get_safe_filename(upload)
    extension = validate_extension(filename, allowed_extensions)

    # A UUID prevents uploaded files with similar names from overwriting
    # each other inside the temporary directory.
    temporary_filename = f"{uuid4().hex}{extension}"
    temporary_path = temporary_directory / temporary_filename

    total_size = 0

    with temporary_path.open("wb") as destination:
        while True:
            chunk = upload.file.read(UPLOAD_CHUNK_SIZE)

            if not chunk:
                break

            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"'{filename}' exceeds the maximum allowed size "
                        f"of {MAX_FILE_SIZE // (1024 * 1024)} MB."
                    ),
                )

            destination.write(chunk)

    if total_size == 0:
        raise HTTPException(
            status_code=400,
            detail=f"'{filename}' is empty.",
        )

    # The response parent key will not contain the extension.
    file_key = Path(filename).stem

    return temporary_path, file_key


def validate_multiple_files(files: list[UploadFile]) -> None:
    """
    Validate the number of files in a multiple-file request.
    """

    if not files:
        raise HTTPException(
            status_code=400,
            detail="At least one file must be uploaded.",
        )

    if len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=(
                f"A maximum of {MAX_FILES_PER_REQUEST} files "
                "can be uploaded in one request."
            ),
        )


def ensure_unique_file_key(
    file_key: str,
    results: dict[str, Any],
) -> None:
    """
    Prevent files with the same name but different extensions
    from overwriting each other in the response.
    """

    if file_key in results:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Duplicate filename '{file_key}'. "
                "Upload files with unique names."
            ),
        )


def extract_purchase_order(pdf_path: Path) -> dict[str, Any]:
    """
    Run all three sections of po_extraction.py and combine their result.
    """

    result = extract_po_details(pdf_path)
    clean_text = extract_clean_text(pdf_path)
    result["items"] = extract_items(clean_text)

    return result


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Proofreading Central Planning API is running.",
        "documentation": "/docs",
    }


@app.get("/api/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/api/extract/work-orders")
def upload_work_orders(
    files: list[UploadFile] = File(
        ...,
        description="Upload one or multiple work-order PDF files",
        json_schema_extra={
            "items": {
                "type": "string",
                "format": "binary",
            }
        },
    ),
) -> dict[str, Any]:
    validate_multiple_files(files)
    results: dict[str, Any] = {}

    try:
        with TemporaryDirectory(prefix="work_orders_") as temp_directory:
            temp_path = Path(temp_directory)

            for upload in files:
                saved_path, file_key = save_uploaded_file(
                    upload=upload,
                    temporary_directory=temp_path,
                    allowed_extensions=PDF_EXTENSIONS,
                )

                ensure_unique_file_key(file_key, results)

                try:
                    results[file_key] = extract_work_orders(saved_path)
                except Exception as error:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Could not extract work-order file "
                            f"'{upload.filename}': {error}"
                        ),
                    ) from error

        return results

    finally:
        for upload in files:
            upload.file.close()


@app.post("/api/proofread")
def proofread_documents(
    work_orders: list[UploadFile] = File(
        ...,
        description="Upload one or multiple work-order PDF files",
        json_schema_extra={
            "items": {
                "type": "string",
                "format": "binary",
            }
        },
    ),
    purchase_order: UploadFile = File(
        ...,
        description="Upload one purchase-order PDF file",
        json_schema_extra={
            "type": "string",
            "format": "binary",
        },
    ),
    booking_sheets: list[UploadFile] = File(
        ...,
        description="Upload one or multiple booking-sheet Excel files",
        json_schema_extra={
            "items": {
                "type": "string",
                "format": "binary",
            }
        },
    ),
) -> dict[str, Any]:
    validate_multiple_files(work_orders)
    validate_multiple_files(booking_sheets)
    all_uploads = [*work_orders, purchase_order, *booking_sheets]

    try:
        with TemporaryDirectory(prefix="proofreading_") as temp_directory:
            temp_path = Path(temp_directory)
            work_order_data: dict[str, list[dict[str, Any]]] = {}
            booking_sheet_data: dict[str, list[dict[str, Any]]] = {}
            work_order_keys: dict[str, None] = {}

            for upload in work_orders:
                filename = get_safe_filename(upload)
                saved_path, file_key = save_uploaded_file(
                    upload=upload,
                    temporary_directory=temp_path,
                    allowed_extensions=PDF_EXTENSIONS,
                )
                ensure_unique_file_key(file_key, work_order_keys)
                work_order_keys[file_key] = None

                try:
                    work_order_data[filename] = extract_work_orders(saved_path)
                except Exception as error:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Could not extract work-order file "
                            f"'{filename}': {error}"
                        ),
                    ) from error

            purchase_order_filename = get_safe_filename(purchase_order)
            purchase_order_path, _ = save_uploaded_file(
                upload=purchase_order,
                temporary_directory=temp_path,
                allowed_extensions=PDF_EXTENSIONS,
            )

            try:
                purchase_order_data = extract_purchase_order(
                    purchase_order_path
                )
            except Exception as error:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Could not extract purchase-order file "
                        f"'{purchase_order_filename}': {error}"
                    ),
                ) from error

            booking_keys: dict[str, None] = {}

            for upload in booking_sheets:
                filename = get_safe_filename(upload)
                saved_path, file_key = save_uploaded_file(
                    upload=upload,
                    temporary_directory=temp_path,
                    allowed_extensions=EXCEL_EXTENSIONS,
                )
                ensure_unique_file_key(file_key, booking_keys)
                booking_keys[file_key] = None

                try:
                    booking_sheet_data[filename] = extract_columns(saved_path)
                except Exception as error:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Could not extract booking-sheet file "
                            f"'{filename}': {error}"
                        ),
                    ) from error

            return build_comparison_response(
                work_order_documents=work_order_data,
                purchase_order=purchase_order_data,
                purchase_order_file=purchase_order_filename,
                booking_sheets=booking_sheet_data,
            )

    finally:
        for upload in all_uploads:
            upload.file.close()


@app.post("/api/extract/purchase-order")
def upload_purchase_order(
    file: UploadFile = File(
        ...,
        description="Upload one purchase-order PDF file",
        json_schema_extra={
            "type": "string",
            "format": "binary",
        },
    ),
) -> dict[str, Any]:
    try:
        with TemporaryDirectory(prefix="purchase_order_") as temp_directory:
            temp_path = Path(temp_directory)

            saved_path, file_key = save_uploaded_file(
                upload=file,
                temporary_directory=temp_path,
                allowed_extensions=PDF_EXTENSIONS,
            )

            try:
                result = extract_purchase_order(saved_path)
            except Exception as error:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Could not extract purchase-order file "
                        f"'{file.filename}': {error}"
                    ),
                ) from error

            return {
                file_key: result,
            }

    finally:
        file.file.close()

@app.post("/api/extract/booking-sheets")
def upload_booking_sheets(
    files: list[UploadFile] = File(
        ...,
        description="Upload one or multiple booking-sheet Excel files",
        json_schema_extra={
            "items": {
                "type": "string",
                "format": "binary",
            }
        },
    ),
) -> dict[str, Any]:
    validate_multiple_files(files)
    results: dict[str, Any] = {}

    try:
        with TemporaryDirectory(prefix="booking_sheets_") as temp_directory:
            temp_path = Path(temp_directory)

            for upload in files:
                saved_path, file_key = save_uploaded_file(
                    upload=upload,
                    temporary_directory=temp_path,
                    allowed_extensions=EXCEL_EXTENSIONS,
                )

                ensure_unique_file_key(file_key, results)

                try:
                    results[file_key] = extract_columns(saved_path)
                except Exception as error:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"Could not extract booking-sheet file "
                            f"'{upload.filename}': {error}"
                        ),
                    ) from error

        return results

    finally:
        for upload in files:
            upload.file.close()
