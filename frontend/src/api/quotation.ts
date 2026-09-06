export type QuotationStatus =
  | "uploaded"
  | "queued"
  | "extracting"
  | "needs_review"
  | "approved"
  | "rejected"
  | "failed";

export interface QuotationDocument {
  id: string;
  quotation_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
}

export interface SupplierQuotation {
  id: string;
  rfq_id: string;
  supplier_name: string;
  supplier_reference?: string | null;
  status: QuotationStatus;
  failure_reason?: string | null;
  created_at: string;
  updated_at: string;
  documents: QuotationDocument[];
}

export interface ExtractedLineItem {
  id: string;
  extracted_quotation_id: string;
  rfq_line_item_id?: string | null;
  description_raw: string;
  quantity: number;
  unit: string;
  unit_price: number;
  currency: string;
  total_price: number; // Supplier-quoted total
  calculated_total_price?: number | null; // ProcureFlow calculated (quantity * unit_price)
  has_discrepancy?: boolean;
  lead_time_days?: number | null;
  confidence: number;
  source_page?: number | null;
  source_evidence?: Record<string, any> | null;
  source_bbox?: Record<string, any> | null;
  human_corrected: boolean;
  is_removed: boolean;
  removal_reason?: string | null;
}

export interface ExtractedLineItemCreate {
  description_raw: string;
  quantity: number;
  unit: string;
  unit_price: number;
  currency: string;
  total_price?: number;
  lead_time_days?: number | null;
  rfq_line_item_id?: string | null;
}

export interface ExtractedField {
  id: string;
  field_name: string;
  raw_value?: string | null;
  normalised_value?: Record<string, any> | null;
  confidence: number;
  source_page?: number | null;
  source_evidence?: Record<string, any> | null;
  source_bbox?: Record<string, any> | null;
  human_corrected: boolean;
}

export interface ExtractedQuotation {
  id: string;
  quotation_id: string;
  extraction_model: string;
  extraction_version: string;
  extracted_at: string;
  overall_confidence: number;
  is_current: boolean;
  notes?: string | null;
  raw_llm_output?: {
    validation_warnings?: string[];
  } | null;
  acknowledged_warnings?: string[];
  line_items: ExtractedLineItem[];
  fields: ExtractedField[];
}

export interface ExtractionValidationStatus {
  can_approve: boolean;
  critical_issues: string[];
  warnings: string[];
  acknowledged_warnings: string[];
}

export interface AuditLogEntry {
  id: string;
  rfq_id: string;
  event_type: string;
  actor_type: string;
  actor_id: string;
  timestamp: string;
  payload?: Record<string, any>;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
const DEV_API_KEY = "procureflow_dev_api_key_12345";

export async function fetchQuotations(params?: {
  rfq_id?: string;
  status?: QuotationStatus;
}): Promise<SupplierQuotation[]> {
  const query = new URLSearchParams();
  if (params?.rfq_id) query.set("rfq_id", params.rfq_id);
  if (params?.status) query.set("status", params.status);

  const res = await fetch(`${API_BASE}/api/v1/quotations?${query.toString()}`, {
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) throw new Error(`Failed to fetch quotations: ${res.statusText}`);
  return res.json();
}

export async function fetchQuotation(id: string): Promise<SupplierQuotation> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${id}`, {
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) throw new Error(`Failed to fetch quotation: ${res.statusText}`);
  return res.json();
}

export async function createQuotation(data: {
  rfq_id: string;
  supplier_name: string;
  supplier_reference?: string;
}): Promise<SupplierQuotation> {
  const res = await fetch(`${API_BASE}/api/v1/quotations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to create quotation: ${res.statusText}`);
  }
  return res.json();
}

export async function uploadQuotationDocument(
  quotationId: string,
  file: File
): Promise<QuotationDocument> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/documents`, {
    method: "POST",
    headers: { "X-API-Key": DEV_API_KEY },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to upload document: ${res.statusText}`);
  }
  return res.json();
}

export async function downloadQuotationDocumentBlob(
  quotationId: string,
  documentId: string
): Promise<{ blob: Blob; filename?: string; mimeType: string }> {
  const res = await fetch(
    `${API_BASE}/api/v1/quotations/${quotationId}/documents/${documentId}/download`,
    {
      headers: { "X-API-Key": DEV_API_KEY },
    }
  );
  if (!res.ok) {
    throw new Error(`Failed to download document: ${res.statusText}`);
  }
  const blob = await res.blob();
  const mimeType = res.headers.get("content-type") || "application/octet-stream";
  const disposition = res.headers.get("content-disposition");
  let filename = "document";
  if (disposition && disposition.includes("filename=")) {
    filename = disposition.split("filename=")[1].replace(/["']/g, "").trim();
  }
  return { blob, filename, mimeType };
}

export async function triggerExtraction(
  quotationId: string
): Promise<{ quotation_id: string; status: string; message?: string }> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/extract`, {
    method: "POST",
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to trigger extraction: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchLatestExtraction(
  quotationId: string
): Promise<ExtractedQuotation> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/extractions/latest`, {
    headers: { "X-API-Key": DEV_API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Extraction result not found: ${res.statusText}`);
  }
  return res.json();
}

export async function createLineItem(
  quotationId: string,
  data: ExtractedLineItemCreate
): Promise<ExtractedLineItem> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/line-items`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to add line item: ${res.statusText}`);
  }
  return res.json();
}

export async function correctLineItem(
  quotationId: string,
  lineItemId: string,
  data: Partial<ExtractedLineItem>
): Promise<ExtractedLineItem> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/line-items/${lineItemId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update line item: ${res.statusText}`);
  }
  return res.json();
}

export async function softDeleteLineItem(
  quotationId: string,
  lineItemId: string,
  reason?: string
): Promise<ExtractedLineItem> {
  const query = reason ? `?reason=${encodeURIComponent(reason)}` : "";
  const res = await fetch(
    `${API_BASE}/api/v1/quotations/${quotationId}/line-items/${lineItemId}${query}`,
    {
      method: "DELETE",
      headers: { "X-API-Key": DEV_API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to exclude line item: ${res.statusText}`);
  }
  return res.json();
}

export async function restoreLineItem(
  quotationId: string,
  lineItemId: string
): Promise<ExtractedLineItem> {
  const res = await fetch(
    `${API_BASE}/api/v1/quotations/${quotationId}/line-items/${lineItemId}/restore`,
    {
      method: "POST",
      headers: { "X-API-Key": DEV_API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to restore line item: ${res.statusText}`);
  }
  return res.json();
}

export async function correctQuotationField(
  quotationId: string,
  fieldId: string,
  data: { raw_value?: string | null; normalised_value?: Record<string, any> | null }
): Promise<ExtractedField> {
  const res = await fetch(
    `${API_BASE}/api/v1/quotations/${quotationId}/fields/${fieldId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": DEV_API_KEY,
      },
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update field: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchValidationStatus(
  quotationId: string
): Promise<ExtractionValidationStatus> {
  const res = await fetch(
    `${API_BASE}/api/v1/quotations/${quotationId}/validation-status`,
    {
      headers: { "X-API-Key": DEV_API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch validation status: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchAuditLogs(
  quotationId: string
): Promise<AuditLogEntry[]> {
  const res = await fetch(
    `${API_BASE}/api/v1/quotations/${quotationId}/audit-logs`,
    {
      headers: { "X-API-Key": DEV_API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to fetch audit logs: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Approve Extraction (reviews extraction quality, does not make supplier award decisions)
 */
export async function approveExtraction(
  quotationId: string,
  acknowledgedWarnings?: string[]
): Promise<SupplierQuotation> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify({
      status: "approved",
      acknowledged_warnings: acknowledgedWarnings,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to approve extraction: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Reject Extraction (reviews extraction quality, does not make supplier award decisions)
 */
export async function rejectExtraction(
  quotationId: string,
  failureReason: string
): Promise<SupplierQuotation> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify({
      status: "rejected",
      failure_reason: failureReason,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to reject extraction: ${res.statusText}`);
  }
  return res.json();
}

// Backward compatibility alias
export const updateQuotationStatus = (
  quotationId: string,
  status: QuotationStatus,
  failure_reason?: string
) => {
  if (status === "approved") {
    return approveExtraction(quotationId);
  } else if (status === "rejected") {
    return rejectExtraction(quotationId, failure_reason || "Rejected during human review");
  } else {
    return fetch(`${API_BASE}/api/v1/quotations/${quotationId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": DEV_API_KEY,
      },
      body: JSON.stringify({ status, failure_reason }),
    }).then(res => res.json());
  }
};
