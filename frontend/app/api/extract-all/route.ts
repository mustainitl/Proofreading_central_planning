import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 300;

const FASTAPI_BASE_URL = (
  process.env.FASTAPI_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");

const PDF_EXTENSIONS = new Set([".pdf"]);
const EXCEL_EXTENSIONS = new Set([".xlsx", ".xls", ".xlsm"]);

function getFiles(formData: FormData, fieldName: string): File[] {
  return formData
    .getAll(fieldName)
    .filter((value): value is File => value instanceof File && value.size > 0);
}

function extensionOf(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex === -1 ? "" : filename.slice(dotIndex).toLowerCase();
}

function invalidFiles(files: File[], allowed: Set<string>): string[] {
  return files
    .filter((file) => !allowed.has(extensionOf(file.name)))
    .map((file) => file.name);
}

function backendErrorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object") {
    return "The proofreading service could not process the documents.";
  }

  const error = payload as { detail?: unknown };

  return typeof error.detail === "string"
    ? error.detail
    : "The proofreading service could not process the documents.";
}

export async function POST(request: Request) {
  let formData: FormData;

  try {
    formData = await request.formData();
  } catch {
    return NextResponse.json(
      { message: "The submitted upload form could not be read." },
      { status: 400 },
    );
  }

  const workOrders = getFiles(formData, "workOrders");
  const purchaseOrders = getFiles(formData, "purchaseOrder");
  const bookingSheets = getFiles(formData, "bookingSheets");
  const validationErrors: string[] = [];

  if (workOrders.length === 0) {
    validationErrors.push("Upload at least one work-order PDF.");
  }

  if (purchaseOrders.length !== 1) {
    validationErrors.push("Upload exactly one purchase-order PDF.");
  }

  if (bookingSheets.length === 0) {
    validationErrors.push("Upload at least one booking-sheet Excel file.");
  }

  const invalidWorkOrders = invalidFiles(workOrders, PDF_EXTENSIONS);
  const invalidPurchaseOrders = invalidFiles(purchaseOrders, PDF_EXTENSIONS);
  const invalidBookingSheets = invalidFiles(bookingSheets, EXCEL_EXTENSIONS);

  if (invalidWorkOrders.length > 0) {
    validationErrors.push(
      `Invalid work-order files: ${invalidWorkOrders.join(", ")}`,
    );
  }

  if (invalidPurchaseOrders.length > 0) {
    validationErrors.push(
      `Invalid purchase-order file: ${invalidPurchaseOrders.join(", ")}`,
    );
  }

  if (invalidBookingSheets.length > 0) {
    validationErrors.push(
      `Invalid booking-sheet files: ${invalidBookingSheets.join(", ")}`,
    );
  }

  if (validationErrors.length > 0) {
    return NextResponse.json(
      {
        message: "Please correct the selected files.",
        errors: validationErrors,
      },
      { status: 400 },
    );
  }

  const backendForm = new FormData();

  workOrders.forEach((file) =>
    backendForm.append("work_orders", file, file.name),
  );
  backendForm.append("purchase_order", purchaseOrders[0], purchaseOrders[0].name);
  bookingSheets.forEach((file) =>
    backendForm.append("booking_sheets", file, file.name),
  );

  try {
    const response = await fetch(`${FASTAPI_BASE_URL}/api/proofread`, {
      method: "POST",
      body: backendForm,
      cache: "no-store",
    });
    const responseText = await response.text();
    let payload: unknown;

    try {
      payload = responseText ? JSON.parse(responseText) : null;
    } catch {
      payload = responseText;
    }

    if (!response.ok) {
      return NextResponse.json(
        {
          message: backendErrorMessage(payload),
          details: payload,
        },
        { status: response.status },
      );
    }

    return NextResponse.json(payload);
  } catch {
    return NextResponse.json(
      {
        message:
          "Could not reach FastAPI. Confirm that the backend server is running.",
      },
      { status: 502 },
    );
  }
}
