export interface CriterionConfig {
  name: string;
  weight: number;
  direction: "MINIMIZE" | "MAXIMIZE";
  source_field: string;
  description?: string | null;
  categorical_map?: Record<string, number> | null;
  knockout_threshold?: number | null;
  knockout_condition?: "GREATER_THAN" | "LESS_THAN" | "GREATER_EQUAL" | "LESS_EQUAL" | "EQUALS" | "NOT_EQUALS" | null;
}

export interface ScoringConfigurationCreate {
  name?: string;
  description?: string;
  criteria: CriterionConfig[];
  missing_value_policy?: "BLOCK_SCORING" | "ZERO_SCORE" | "WORST_IN_COHORT";
  tie_policy?: "STANDARD_COMPETITION" | "FRACTIONAL";
}

export interface ScoringConfigurationResponse {
  id: string;
  rfq_id: string;
  version: number;
  name: string;
  description?: string | null;
  criteria: CriterionConfig[];
  missing_value_policy: string;
  tie_policy: string;
  is_active: boolean;
  created_at: string;
}

export interface CriterionScoreBreakdown {
  raw_value: number | string | null;
  cohort_min?: number | null;
  cohort_max?: number | null;
  normalized_score: number; // 0.00 to 100.00
  weight: number;
  weighted_contribution: number;
  knockout_applied: boolean;
  notes?: string | null;
  source_path?: string | null;
}

export interface SupplierScore {
  quotation_id: string;
  supplier_name: string;
  is_eligible: boolean;
  status: "eligible" | "ineligible" | "knockout_failed";
  knockout_reasons: string[];
  composite_score: number; // 0.00 to 100.00
  rank?: number | null;
  breakdown: Record<string, CriterionScoreBreakdown>;
}

export interface ScoringRunCreate {
  scoring_configuration_id: string;
  comparison_snapshot_id: string;
  notes?: string;
}

export interface ScoringRunResponse {
  id: string;
  rfq_id: string;
  scoring_configuration_id: string;
  scoring_configuration_version: number;
  comparison_snapshot_id: string;
  comparison_snapshot_version: number;
  comparison_snapshot_hash?: string | null;
  scores: SupplierScore[];
  notes?: string | null;
  created_at: string;
}

export interface ScoringSimulationRequest {
  comparison_snapshot_id: string;
  scoring_configuration_id?: string;
  transient_criteria?: CriterionConfig[];
}

export interface SensitivityRequest {
  comparison_snapshot_id: string;
  scoring_configuration_id?: string;
  sweep_criterion: string;
  min_weight?: number;
  max_weight?: number;
  step?: number;
  locked_criteria?: Record<string, number>;
  target_supplier_id?: string;
}

export interface SensitivityPoint {
  weight: number;
  weights_vector: Record<string, number>;
  supplier_scores: Record<string, number>;
  ranks: Record<string, number>;
}

export interface CrossoverPoint {
  weight: number;
  supplier_a_id: string;
  supplier_a_name: string;
  supplier_b_id: string;
  supplier_b_name: string;
  score_at_crossover: number;
  description: string;
}

export interface BreakevenResult {
  target_supplier_id: string;
  target_supplier_name: string;
  current_rank: number;
  current_score: number;
  target_rank: number;
  incumbent_supplier_id?: string | null;
  incumbent_supplier_name?: string | null;
  required_score: number;
  current_price?: number | null;
  required_price?: number | null;
  price_delta?: number | null;
  percentage_reduction_needed?: number | null;
  is_feasible: boolean;
  bisection_iterations?: number | null;
  explanation: string;
}

export interface SensitivityResponse {
  comparison_snapshot_id: string;
  sweep_criterion: string;
  data_points: SensitivityPoint[];
  crossover_points: CrossoverPoint[];
  breakeven?: BreakevenResult | null;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const API_KEY = "procureflow_dev_api_key_12345";

export async function fetchScoringConfigurations(rfqId: string): Promise<ScoringConfigurationResponse[]> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/configurations`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch scoring configurations");
  }
  return res.json();
}

export async function fetchActiveScoringConfiguration(rfqId: string): Promise<ScoringConfigurationResponse | null> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/configurations/active`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (res.status === 404) return null;
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch active scoring configuration");
  }
  return res.json();
}

export async function createScoringConfiguration(
  rfqId: string,
  data: ScoringConfigurationCreate
): Promise<ScoringConfigurationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/configurations`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create scoring configuration");
  }
  return res.json();
}

export async function fetchScoringRuns(rfqId: string): Promise<ScoringRunResponse[]> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/runs`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch scoring runs");
  }
  return res.json();
}

export async function fetchScoringRun(rfqId: string, runId: string): Promise<ScoringRunResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/runs/${runId}`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to fetch scoring run");
  }
  return res.json();
}

export async function createScoringRun(
  rfqId: string,
  data: ScoringRunCreate
): Promise<ScoringRunResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to execute scoring run");
  }
  return res.json();
}

export async function simulateScoring(
  rfqId: string,
  data: ScoringSimulationRequest
): Promise<{ snapshot_id: string; scores: SupplierScore[]; criteria: CriterionConfig[] }> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/simulate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to simulate scoring");
  }
  return res.json();
}

export async function runSensitivityAnalysis(
  rfqId: string,
  data: SensitivityRequest
): Promise<SensitivityResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/scoring/sensitivity`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to compute sensitivity analysis");
  }
  return res.json();
}
