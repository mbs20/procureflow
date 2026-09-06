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
  total_price: number;
  calculated_total_price?: number | null;
  has_discrepancy?: boolean;
  lead_time_days?: number | null;
  confidence: number;
  source_page?: number | null;
  source_evidence?: Record<string, any> | null;
  source_bbox?: Record<string, any> | null;
  human_corrected: boolean;
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
  line_items: ExtractedLineItem[];
  fields: ExtractedField[];
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

export async function updateQuotationStatus(
  quotationId: string,
  status: QuotationStatus,
  failure_reason?: string
): Promise<SupplierQuotation> {
  const res = await fetch(`${API_BASE}/api/v1/quotations/${quotationId}/status`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": DEV_API_KEY,
    },
    body: JSON.stringify({ status, failure_reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed to update status: ${res.statusText}`);
  }
  return res.json();
}
