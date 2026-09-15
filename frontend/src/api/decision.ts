/**
 * Phase 6 — API client for Decision Narrative & Human Award Workflow.
 */

export type NarrativeType =
  | "comparison_summary"
  | "tradeoff_analysis"
  | "sensitivity_summary"
  | "decision_support_memo"
  | "decision_considerations";

export type NarrativeOrigin = "ai_generated" | "ai_generated_human_revised" | "human_authored";
export type ClaimType = "deterministic_fact" | "interpretation" | "limitation";
export type GroundingStatus = "verified" | "unsupported" | "unverifiable";
export type AwardStatus = "draft" | "confirmed" | "revoked";
export type AwardEventType = "draft_created" | "confirmed" | "revoked";

export interface FactReference {
  reference_type: string;
  field_path?: string;
  authoritative_value?: string;
  criterion_id?: string;
  supplier_id?: string;
  evidence_id?: string;
}

export interface NarrativeClaim {
  id: string;
  claim_index: number;
  text: string;
  claim_type: ClaimType;
  grounding_status: GroundingStatus;
  referenced_supplier_ids: string[];
  referenced_criterion_ids: string[];
  referenced_evidence_ids: string[];
  fact_references?: FactReference[] | Record<string, any> | null;
  grounding_notes?: string | null;
}

export interface NarrativeRevision {
  id: string;
  narrative_generation_id: string;
  revision_number: number;
  revised_text: string;
  revision_rationale?: string | null;
  revised_by: string;
  created_at: string;
}

export interface SupplierAnalysis {
  supplier_id: string;
  supplier_name: string;
  rank?: number | null;
  total_score: string;
  strengths: string[];
  weaknesses: string[];
  score_context: string;
}

export interface NarrativeSections {
  executive_summary: string;
  ranking_explanation: string;
  per_supplier_analysis: SupplierAnalysis[];
  trade_offs: string;
  decision_considerations: string;
  risk_factors: string[];
  data_limitations: string[];
}

export interface GroundingValidationResult {
  total_claims: number;
  verified: number;
  unsupported: number;
  unverifiable: number;
  details: Array<{
    claim_index: number;
    status: string;
    issues: string[];
  }>;
}

export interface NarrativeGenerationResponse {
  id: string;
  rfq_id: string;
  decision_context_id: string;
  narrative_type: NarrativeType;
  generation_number: number;
  origin: NarrativeOrigin;
  provider: string;
  model_identifier: string;
  prompt_template_version: string;
  prompt_template_hash: string;
  rendered_prompt_hash: string;
  response_schema_version: string;
  generation_parameters: Record<string, any>;
  raw_structured_output: NarrativeSections;
  output_hash: string;
  grounding_validation_result: GroundingValidationResult;
  is_superseded: boolean;
  superseded_reason?: string | null;
  generated_at: string;
  created_by: string;
  claims: NarrativeClaim[];
  revisions: NarrativeRevision[];
  current_origin: NarrativeOrigin;
}

export interface NarrativeGenerationRequest {
  scoring_run_id: string;
  narrative_type?: NarrativeType;
  include_sensitivity?: boolean;
  human_unverified_note?: string | null;
}

export interface DecisionContextResponse {
  id: string;
  rfq_id: string;
  scoring_run_id: string;
  context_schema_version: string;
  context_payload: Record<string, any>;
  context_hash: string;
  includes_sensitivity: boolean;
  created_by: string;
  created_at: string;
}

export interface AwardDecisionEvent {
  id: string;
  award_decision_id: string;
  event_type: AwardEventType;
  event_number: number;
  event_payload: Record<string, any>;
  actor_principal: string;
  actor_display_name?: string | null;
  created_at: string;
}

export interface AwardDecisionResponse {
  id: string;
  rfq_id: string;
  scoring_run_id: string;
  narrative_generation_id?: string | null;
  awarded_supplier_id: string;
  awarded_supplier_name: string;
  awarded_supplier_rank?: number | null;
  non_rank1_rationale?: string | null;
  current_status: AwardStatus;
  provenance_hash?: string | null;
  created_by: string;
  created_at: string;
  events: AwardDecisionEvent[];
  is_based_on_latest_run: boolean;
  latest_scoring_run_id?: string | null;
}

export interface AwardDecisionCreate {
  scoring_run_id: string;
  awarded_supplier_id: string;
  award_justification: string;
  narrative_generation_id?: string | null;
  non_rank1_rationale?: string | null;
}

export interface AwardConfirm {
  final_justification?: string | null;
}

export interface AwardRevoke {
  revocation_reason: string;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";
const API_KEY = "procureflow_dev_api_key_12345";

export async function generateNarrative(
  rfqId: string,
  data: NarrativeGenerationRequest
): Promise<NarrativeGenerationResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/decisions/narratives`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to generate narrative");
  }
  return res.json();
}

export async function listNarratives(
  rfqId: string,
  scoringRunId?: string
): Promise<NarrativeGenerationResponse[]> {
  const query = scoringRunId ? `?scoring_run_id=${encodeURIComponent(scoringRunId)}` : "";
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/decisions/narratives${query}`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list narratives");
  }
  return res.json();
}

export async function getNarrative(
  rfqId: string,
  narrativeId: string
): Promise<NarrativeGenerationResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/rfqs/${rfqId}/decisions/narratives/${narrativeId}`,
    {
      headers: { "X-API-Key": API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to get narrative");
  }
  return res.json();
}

export async function createNarrativeRevision(
  rfqId: string,
  narrativeId: string,
  revisedText: string,
  rationale?: string
): Promise<NarrativeRevision> {
  const res = await fetch(
    `${API_BASE}/api/v1/rfqs/${rfqId}/decisions/narratives/${narrativeId}/revisions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify({
        revised_text: revisedText,
        revision_rationale: rationale,
      }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to record narrative revision");
  }
  return res.json();
}

export async function getDecisionContext(
  rfqId: string,
  contextId: string
): Promise<DecisionContextResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/rfqs/${rfqId}/decisions/contexts/${contextId}`,
    {
      headers: { "X-API-Key": API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to get decision context");
  }
  return res.json();
}

export async function createDraftAward(
  rfqId: string,
  data: AwardDecisionCreate
): Promise<AwardDecisionResponse> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/decisions/awards`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to create draft award");
  }
  return res.json();
}

export async function listAwards(rfqId: string): Promise<AwardDecisionResponse[]> {
  const res = await fetch(`${API_BASE}/api/v1/rfqs/${rfqId}/decisions/awards`, {
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to list awards");
  }
  return res.json();
}

export async function getCurrentAward(
  rfqId: string
): Promise<AwardDecisionResponse | null> {
  const res = await fetch(
    `${API_BASE}/api/v1/rfqs/${rfqId}/decisions/awards/current`,
    {
      headers: { "X-API-Key": API_KEY },
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to get current award");
  }
  return res.json();
}

export async function confirmAward(
  rfqId: string,
  awardId: string,
  data: AwardConfirm
): Promise<AwardDecisionResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/rfqs/${rfqId}/decisions/awards/${awardId}/confirm`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to confirm award");
  }
  return res.json();
}

export async function revokeAward(
  rfqId: string,
  awardId: string,
  data: AwardRevoke
): Promise<AwardDecisionResponse> {
  const res = await fetch(
    `${API_BASE}/api/v1/rfqs/${rfqId}/decisions/awards/${awardId}/revoke`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to revoke award");
  }
  return res.json();
}
