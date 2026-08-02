"use client";

import {
  ChangeEvent,
  DragEvent,
  ReactNode,
  useMemo,
  useRef,
  useState,
} from "react";

type ComparisonStatus = "match" | "mismatch" | "missing" | "review";

type ComparisonRow = {
  field: string;
  work_order: string | number | null;
  purchase_order: string | number | null;
  booking_sheet: string | number | null;
  status: ComparisonStatus;
  message?: string | null;
};

type WorkOrderResult = {
  work_order_no: string;
  source_file: string;
  status: ComparisonStatus;
  rows: ComparisonRow[];
  size_rows: ComparisonRow[];
};

type ExtractionResult = {
  generated_at: string;
  summary: {
    overall_status: ComparisonStatus;
    total_work_orders: number;
    total_fields: number;
    matched: number;
    mismatched: number;
    missing: number;
    review: number;
  };
  work_orders: WorkOrderResult[];
};

type UploadCardProps = {
  accent: "blue" | "green" | "violet";
  accept: string;
  description: string;
  files: File[];
  icon: ReactNode;
  id: string;
  multiple: boolean;
  onFiles: (files: File[]) => void;
  onRemove: (index: number) => void;
  requiredText: string;
  title: string;
};

const FILE_RULES = {
  workOrders: new Set(["pdf"]),
  purchaseOrder: new Set(["pdf"]),
  bookingSheets: new Set(["xlsx", "xls", "xlsm"]),
};

function fileExtension(filename: string) {
  return filename.split(".").pop()?.toLowerCase() ?? "";
}

function formatFileSize(size: number) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function deduplicateFiles(files: File[]) {
  const seen = new Set<string>();

  return files.filter((file) => {
    const identity = `${file.name}-${file.size}-${file.lastModified}`;

    if (seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
}

function DocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M7.75 3.5h5.9l3.85 3.85v13.15H7.75a2.25 2.25 0 0 1-2.25-2.25V5.75A2.25 2.25 0 0 1 7.75 3.5Z" />
      <path d="M13.5 3.75V7.5h3.75M8.75 11h5.75M8.75 14.5h5.75M8.75 18h3.5" />
    </svg>
  );
}

function CartIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 5h2l1.45 9.2a2 2 0 0 0 1.98 1.68h7.82a2 2 0 0 0 1.96-1.6L20.5 8H7" />
      <circle cx="10" cy="19" r="1.35" />
      <circle cx="17" cy="19" r="1.35" />
    </svg>
  );
}

function SheetIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="4" y="3.5" width="16" height="17" rx="2.25" />
      <path d="M8 8h8M8 12h8M8 16h8M12 8v8" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 16V4M7.5 8.5 12 4l4.5 4.5M5 14.5v4.25A1.25 1.25 0 0 0 6.25 20h11.5A1.25 1.25 0 0 0 19 18.75V14.5" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m5 12.5 4.25 4.25L19 7" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m7 7 10 10M17 7 7 17" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="8" y="8" width="11" height="11" rx="2" />
      <path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4v11M7.5 11.5 12 16l4.5-4.5M5 20h14" />
    </svg>
  );
}

function RefreshIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M19 7.5V4m0 0h-3.5M19 4a8 8 0 1 0 1 9.9" />
    </svg>
  );
}

function UploadCard({
  accent,
  accept,
  description,
  files,
  icon,
  id,
  multiple,
  onFiles,
  onRemove,
  requiredText,
  title,
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  function receiveFiles(nextFiles: FileList | null) {
    if (!nextFiles) return;
    onFiles(Array.from(nextFiles));
  }

  function handleChange(event: ChangeEvent<HTMLInputElement>) {
    receiveFiles(event.target.files);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    receiveFiles(event.dataTransfer.files);
  }

  return (
    <article className={`upload-card accent-${accent}`}>
      <div className="upload-card-heading">
        <span className="upload-card-icon">{icon}</span>
        <div>
          <div className="title-line">
            <h2>{title}</h2>
            <span className="required-badge">Required</span>
          </div>
          <p>{description}</p>
        </div>
      </div>

      <div
        className={`drop-zone ${dragging ? "is-dragging" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragEnter={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={(event) => {
          event.preventDefault();
          setDragging(false);
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label={`Choose ${title.toLowerCase()} files`}
      >
        <span className="upload-mark">
          <UploadIcon />
        </span>
        <strong>Drop files here or browse</strong>
        <span>{requiredText}</span>
        <input
          ref={inputRef}
          id={id}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={handleChange}
          tabIndex={-1}
        />
      </div>

      <div className="selected-files" aria-live="polite">
        <div className="selected-files-label">
          <span>Selected files</span>
          <span>{files.length}</span>
        </div>

        {files.length === 0 ? (
          <p className="empty-file-list">No files selected yet</p>
        ) : (
          <ul>
            {files.map((file, index) => (
              <li key={`${file.name}-${file.lastModified}-${index}`}>
                <span className="file-type">
                  {fileExtension(file.name).toUpperCase()}
                </span>
                <span className="file-details">
                  <strong title={file.name}>{file.name}</strong>
                  <small>{formatFileSize(file.size)}</small>
                </span>
                <button
                  type="button"
                  onClick={() => onRemove(index)}
                  aria-label={`Remove ${file.name}`}
                >
                  <CloseIcon />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}

function StatusBadge({ status }: { status: ComparisonStatus }) {
  return (
    <span className={`status-badge status-${status}`}>
      <i>{status === "match" ? <CheckIcon /> : null}</i>
      {status}
    </span>
  );
}

function displayValue(value: string | number | null) {
  return value === null || value === "" ? "-" : String(value);
}


function ResultRowsTable({
  title,
  rows,
}: {
  title: string;
  rows: ComparisonRow[];
}) {
  if (rows.length === 0) {
    return null;
  }

  return (
    <section className="comparison-table-section">
      <h4>{title}</h4>

      <div className="comparison-table-scroll">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Fields</th>
              <th>Work Order</th>
              <th>Purchase Order</th>
              <th>Booking Sheet</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((row, index) => (
              <tr key={`${row.field}-${index}`}>
                <th scope="row">{row.field}</th>
                <td>{displayValue(row.work_order)}</td>
                <td>{displayValue(row.purchase_order)}</td>
                <td>{displayValue(row.booking_sheet)}</td>
                <td>
                  <StatusBadge status={row.status} />

                  {row.message ? (
                    <p className="comparison-message">
                      {row.message}
                    </p>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}


function ComparisonTable({ result }: { result: WorkOrderResult }) {
  return (
    <article className="comparison-card">
      <div className="comparison-card-heading">
        <div>
          <span>Work order</span>
          <h3>{result.work_order_no}</h3>
          <p>{result.source_file}</p>
        </div>
        <StatusBadge status={result.status} />
      </div>

      <ResultRowsTable
        title="General comparisons"
        rows={result.rows}
      />

      <ResultRowsTable
        title="Size, PO line and quantity comparisons"
        rows={result.size_rows}
      />
    </article>
  );
}

function readableError(payload: unknown) {
  if (!payload || typeof payload !== "object") {
    return "Extraction failed. Please try again.";
  }

  const candidate = payload as {
    message?: string;
    errors?: unknown;
  };

  if (candidate.message) return candidate.message;
  return "Extraction failed. Please review the selected files.";
}

export default function UploadDashboard() {
  const [workOrders, setWorkOrders] = useState<File[]>([]);
  const [purchaseOrder, setPurchaseOrder] = useState<File[]>([]);
  const [bookingSheets, setBookingSheets] = useState<File[]>([]);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorDetails, setErrorDetails] = useState<unknown>(null);
  const [isExtracting, setIsExtracting] = useState(false);
  const [copied, setCopied] = useState(false);

  const isReady =
    workOrders.length > 0 &&
    purchaseOrder.length === 1 &&
    bookingSheets.length > 0;

  const selectedCount =
    workOrders.length + purchaseOrder.length + bookingSheets.length;

  const readiness = useMemo(
    () => [
      { label: "Work orders", ready: workOrders.length > 0 },
      { label: "Purchase order", ready: purchaseOrder.length === 1 },
      { label: "Booking sheets", ready: bookingSheets.length > 0 },
    ],
    [workOrders.length, purchaseOrder.length, bookingSheets.length],
  );

  function addFiles(
    current: File[],
    incoming: File[],
    allowed: Set<string>,
    multiple: boolean,
    setter: (files: File[]) => void,
  ) {
    setError(null);
    setErrorDetails(null);

    const invalid = incoming.filter(
      (file) => !allowed.has(fileExtension(file.name)),
    );

    if (invalid.length > 0) {
      setError(
        `Unsupported file type: ${invalid.map((file) => file.name).join(", ")}`,
      );
      return;
    }

    const nextFiles = multiple
      ? deduplicateFiles([...current, ...incoming])
      : incoming.slice(0, 1);

    setter(nextFiles);
    setResult(null);
  }

  async function handleExtract() {
    if (!isReady || isExtracting) return;

    setIsExtracting(true);
    setError(null);
    setErrorDetails(null);
    setResult(null);

    const formData = new FormData();
    workOrders.forEach((file) => formData.append("workOrders", file));
    formData.append("purchaseOrder", purchaseOrder[0]);
    bookingSheets.forEach((file) => formData.append("bookingSheets", file));

    try {
      const response = await fetch("/api/extract-all", {
        method: "POST",
        body: formData,
      });

      const payload = await response.json();

      if (!response.ok) {
        setError(readableError(payload));
        setErrorDetails(payload);
        return;
      }

      setResult(payload as ExtractionResult);
    } catch {
      setError(
        "The frontend could not complete the request. Confirm both servers are running.",
      );
    } finally {
      setIsExtracting(false);
    }
  }

  function resetWorkspace() {
    setWorkOrders([]);
    setPurchaseOrder([]);
    setBookingSheets([]);
    setResult(null);
    setError(null);
    setErrorDetails(null);
    setCopied(false);
  }

  async function copyResult() {
    if (!result) return;
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  }

  function downloadResult() {
    if (!result) return;

    const blob = new Blob([JSON.stringify(result, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `extraction-${new Date()
      .toISOString()
      .replace(/[:.]/g, "-")}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">
            <span />
            <span />
            <span />
          </span>
          <span>
            <strong>Proofread</strong>
            <small>Document intelligence</small>
          </span>
        </div>

        <div className="workspace-status">
          <span className="status-dot" />
          Extraction workspace
        </div>
      </header>

      <section className="workspace-panel">
        <div className="section-heading">
          <div>
            <span className="section-kicker">Document set</span>
            <h2>Choose source files</h2>
          </div>
          <div className="selection-count">
            <strong>{selectedCount}</strong>
            <span>files selected</span>
          </div>
        </div>

        <div className="upload-grid">
          <UploadCard
            accent="blue"
            accept=".pdf,application/pdf"
            description="Production work-order documents"
            files={workOrders}
            icon={<DocumentIcon />}
            id="work-orders"
            multiple
            onFiles={(files) =>
              addFiles(
                workOrders,
                files,
                FILE_RULES.workOrders,
                true,
                setWorkOrders,
              )
            }
            onRemove={(index) =>
              setWorkOrders((files) =>
                files.filter((_, fileIndex) => fileIndex !== index),
              )
            }
            requiredText="PDF · One or multiple files"
            title="Work orders"
          />

          <UploadCard
            accent="green"
            accept=".pdf,application/pdf"
            description="The matching purchase-order document"
            files={purchaseOrder}
            icon={<CartIcon />}
            id="purchase-order"
            multiple={false}
            onFiles={(files) =>
              addFiles(
                purchaseOrder,
                files,
                FILE_RULES.purchaseOrder,
                false,
                setPurchaseOrder,
              )
            }
            onRemove={() => setPurchaseOrder([])}
            requiredText="PDF · One file only"
            title="Purchase order"
          />

          <UploadCard
            accent="violet"
            accept=".xlsx,.xls,.xlsm"
            description="Product and booking reference sheets"
            files={bookingSheets}
            icon={<SheetIcon />}
            id="booking-sheets"
            multiple
            onFiles={(files) =>
              addFiles(
                bookingSheets,
                files,
                FILE_RULES.bookingSheets,
                true,
                setBookingSheets,
              )
            }
            onRemove={(index) =>
              setBookingSheets((files) =>
                files.filter((_, fileIndex) => fileIndex !== index),
              )
            }
            requiredText="XLSX, XLS, XLSM · One or multiple"
            title="Booking sheets"
          />
        </div>

        {error && (
          <div className="error-banner" role="alert">
            <span>!</span>
            <div>
              <strong>{error}</strong>
              {errorDetails !== null && (
                <details>
                  <summary>View technical details</summary>
                  <pre>{JSON.stringify(errorDetails, null, 2)}</pre>
                </details>
              )}
            </div>
          </div>
        )}

        <div className="action-bar">
          <div className="readiness-list">
            {readiness.map((item) => (
              <span className={item.ready ? "ready" : ""} key={item.label}>
                <i>{item.ready ? <CheckIcon /> : null}</i>
                {item.label}
              </span>
            ))}
          </div>

          <button
            className="extract-button"
            type="button"
            disabled={!isReady || isExtracting}
            onClick={handleExtract}
          >
            {isExtracting ? (
              <>
                <span className="spinner" />
                Extracting documents…
              </>
            ) : (
              <>
                Extract all information
                <span className="button-arrow">→</span>
              </>
            )}
          </button>
        </div>
      </section>

      {result && (
        <section className="results-panel">
          <div className="results-heading">
            <div>
              <span className="success-label">
                <CheckIcon />
                Proofreading complete
              </span>
              <h2>Comparison results</h2>
              <p>
                Completed{" "}
                {new Date(result.generated_at).toLocaleString(undefined, {
                  dateStyle: "medium",
                  timeStyle: "short",
                })}
              </p>
            </div>

            <div className="result-actions">
              <button type="button" onClick={copyResult}>
                <CopyIcon />
                {copied ? "Copied" : "Copy JSON"}
              </button>
              <button type="button" onClick={downloadResult}>
                <DownloadIcon />
                Download
              </button>
              <button type="button" onClick={resetWorkspace}>
                <RefreshIcon />
                New extraction
              </button>
            </div>
          </div>

          <div className="comparison-summary">
            <div className="summary-overall">
              <span>Overall status</span>
              <StatusBadge status={result.summary.overall_status} />
            </div>
            <div>
              <strong>{result.summary.total_fields}</strong>
              <span>Total fields</span>
            </div>
            <div>
              <strong>{result.summary.matched}</strong>
              <span>Matched</span>
            </div>
            <div>
              <strong>{result.summary.mismatched}</strong>
              <span>Mismatched</span>
            </div>
            <div>
              <strong>{result.summary.missing}</strong>
              <span>Missing</span>
            </div>
            <div>
              <strong>{result.summary.review}</strong>
              <span>Review</span>
            </div>
          </div>

          <div className="comparison-list">
            {result.work_orders.map((workOrder) => (
              <ComparisonTable
                key={`${workOrder.source_file}-${workOrder.work_order_no}`}
                result={workOrder}
              />
            ))}
          </div>
        </section>
      )}

      <footer>
        <span>Proofread extraction workspace</span>
        <span>Files are processed temporarily and are not stored.</span>
      </footer>
    </div>
  );
}
