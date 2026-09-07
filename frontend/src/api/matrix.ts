export interface MatrixSupplierHeader {
  quotation_id: string;
  supplier_name: string;
  supplier_reference?: string | null;
  status: string;
  extraction_version: string;
  original_currency: string;
  rfq_coverage_pct: number;
  quoted_items_count: number;
  total_rfq_items: number;
  quoted_grand_total: number;
  normalized_line_item_subtotal: number;
  normalized_comparable_total?: number | null;
  has_unknown_commercial_components: boolean;
  payment_terms_original: string;
  payment_terms_normalized: string;
  payment_terms_code: string;
  overall_lead_time_original: string;
  overall_lead_time_normalized: string;
  overall_lead_time_days?: number | null;
  unresolved_count: number;
  warnings_count: number;
  warnings: string[];
}

export interface MatrixLineItemCell {
  is_quoted: boolean;
  line_item_id?: string | null;
  quoted_description?: string | null;
  quoted_quantity?: number | null;
  quoted_unit?: string | null;
  quoted_unit_price?: number | null;
  quoted_total_price?: number | null;
  calculated_total_price?: number | null;
  has_math_discrepancy: boolean;
  math_discrepancy_amount?: number | null;
  original_currency?: string | null;

  canonical_quantity?: number | null;
  canonical_unit?: string | null;
  uom_conversion_factor?: number | null;
  uom_status: string;
  uom_warning?: string | null;

  fx_rate_used?: number | null;
  fx_effective_date?: string | null;
  fx_provider_id?: string | null;
  fx_status: string;
  fx_warning?: string | null;

  normalized_unit_price?: number | null;
  normalized_extended_price?: number | null;

  line_lead_time_days?: number | null;
  line_lead_time_display?: string | null;
  line_lead_time_type?: string | null;

  overall_cell_status: string;
  is_human_overridden: boolean;
  override_id?: string | null;
  override_reason?: string | null;
  warnings: string[];
  source_evidence?: any;
  source_page?: number | null;
}

export interface MatrixRequiredRow {
  rfq_line_item_id: string;
  position: number;
  description: string;
  required_quantity: number;
  required_unit: string;
  supplier_cells: Record<string, MatrixLineItemCell>;
}

export interface MatrixExtraItem {
  line_item_id: string;
  quotation_id: string;
  supplier_name: string;
  description_raw: string;
  quantity: number;
  unit: string;
  unit_price: number;
  currency: string;
  total_price: number;
  lead_time_days?: number | null;
  source_page?: number | null;
}

export interface RFQFXRateSetRead {
  id: string;
  rfq_id: string;
  version: number;
  base_currency: string;
  effective_date: string;
  provider_id: string;
  is_synthetic: boolean;
  rates: Record<string, number>;
  created_by: string;
  created_at: string;
  is_current: boolean;
}

export interface RFQFXRateSetCreate {
  base_currency: string;
  effective_date?: string;
  provider_id?: string;
  is_synthetic?: boolean;
  rates: Record<string, number>;
}

export interface NormalizationOverrideCreate {
  quotation_id: string;
  line_item_id?: string | null;
  field_name: string;
  override_value: Record<string, any>;
  override_reason: string;
}

export interface NormalizationOverrideRead {
  id: string;
  rfq_id: string;
  quotation_id: string;
  line_item_id?: string | null;
  field_name: string;
  original_value: Record<string, any>;
  previous_normalized_value?: Record<string, any> | null;
  override_value: Record<string, any>;
  override_reason: string;
  actor_id: string;
  created_at: string;
  is_active: boolean;
  reverted_at?: string | null;
  reverted_by?: string | null;
  revert_reason?: string | null;
}

export interface ComparisonSnapshotRead {
  id: string;
  rfq_id: string;
  snapshot_version: number;
  normalization_engine_version: string;
  reference_currency: string;
  fx_rate_set_id?: string | null;
  title?: string | null;
  matrix_data: any;
  created_by: string;
  created_at: string;
}

export interface ComparisonMatrixResponse {
  rfq_id: string;
  rfq_title: string;
  reference_currency: string;
  normalization_engine_version: string;
  fx_rate_set?: RFQFXRateSetRead | null;
  suppliers: MatrixSupplierHeader[];
  required_line_items: MatrixRequiredRow[];
  extra_line_items: MatrixExtraItem[];
  active_overrides_count: number;
  snapshots_count: number;
  warnings_summary: string[];
  computed_at: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function fetchComparisonMatrix(
  rfqId: string,
  fxRateSetId?: string
): Promise<ComparisonMatrixResponse> {
  const params = fxRateSetId ? `?fx_rate_set_id=${encodeURIComponent(fxRateSetId)}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to load comparison matrix");
  }
  return res.json();
}

export async function fetchRFQFXRates(rfqId: string): Promise<RFQFXRateSetRead> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/fx-rates`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to load RFQ FX rates");
  }
  return res.json();
}

export async function updateRFQFXRates(
  rfqId: string,
  data: RFQFXRateSetCreate
): Promise<RFQFXRateSetRead> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/fx-rates`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "procureflow_dev_api_key_12345",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to configure RFQ FX rates");
  }
  return res.json();
}

export async function applyNormalizationOverride(
  rfqId: string,
  data: NormalizationOverrideCreate
): Promise<NormalizationOverrideRead> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/overrides`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "procureflow_dev_api_key_12345",
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to apply normalization override");
  }
  return res.json();
}

export async function revertNormalizationOverride(
  rfqId: string,
  overrideId: string,
  revertReason: string = "Reverted to deterministic default"
): Promise<NormalizationOverrideRead> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/overrides/${overrideId}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "procureflow_dev_api_key_12345",
    },
    body: JSON.stringify({ revert_reason: revertReason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to revert normalization override");
  }
  return res.json();
}

export async function createComparisonSnapshot(
  rfqId: string,
  title?: string
): Promise<ComparisonSnapshotRead> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/snapshots`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": "procureflow_dev_api_key_12345",
    },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to freeze comparison snapshot");
  }
  return res.json();
}

export async function listComparisonSnapshots(
  rfqId: string
): Promise<ComparisonSnapshotRead[]> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/matrix/snapshots`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list comparison snapshots");
  }
  return res.json();
}
