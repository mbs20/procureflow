import type {
  APIErrorPayload, BreakevenResult, CriterionConfig, CriterionScoreBreakdown, EligibilityStatus,
  Ranking, ScoringConfigurationCreate, ScoringConfigurationResponse,
  ScoringRunResponse, SensitivityRequest, SensitivityResponse, SupplierScore,
} from "./scoring";

// Validate untrusted JSON at the boundary; exact decimal strings stay authoritative.
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Invalid scoring object");
  }
  return value as Record<string, unknown>;
}

export function readErrorPayload(value: unknown): APIErrorPayload {
  if (!value || typeof value !== "object" || Array.isArray(value)) return { detail: value };
  const raw = object(value);
  return { detail: raw.detail ?? raw.msg, message: raw.message };
}

export function list(value: unknown): unknown[] {
  if (!Array.isArray(value)) throw new Error("Invalid scoring list");
  return value;
}

function text(value: unknown): string {
  if (typeof value !== "string" || !value.trim()) throw new Error("Invalid scoring text");
  return value;
}

function optionalText(value: unknown): string | undefined {
  if (value == null) return undefined;
  if (typeof value !== "string") throw new Error("Invalid scoring text");
  return value;
}

function numeric(value: unknown): number {
  if ((typeof value !== "number" && typeof value !== "string") ||
      String(value).trim() === "" || !Number.isFinite(Number(value))) {
    throw new Error("Invalid scoring number");
  }
  return Number(value);
}

function optionalNumber(value: unknown): number | undefined {
  return value == null ? undefined : numeric(value);
}

function boolean(value: unknown): boolean {
  if (typeof value !== "boolean") throw new Error("Invalid scoring boolean");
  return value;
}

function rank(value: unknown): Ranking {
  if (value == null) return null;
  const result = numeric(value);
  if (!Number.isInteger(result) || result < 1) throw new Error("Invalid scoring rank");
  return result;
}

function numbers(value: unknown): Record<string, number> {
  return Object.fromEntries(Object.entries(object(value)).map(([key, item]) => [key, numeric(item)]));
}

function eligibility(value: unknown): EligibilityStatus {
  switch (value) {
    case "eligible": case "ineligible": case "knockout_failed": case "missing_value_blocked":
      return value;
    default: throw new Error("Invalid scoring eligibility");
  }
}

function readCriterion(value: unknown): CriterionConfig {
  const raw = object(value);
  let direction: CriterionConfig["direction"];
  switch (raw.direction) {
    case "lower_is_better": case "MINIMIZE": direction = "MINIMIZE"; break;
    case "higher_is_better": case "MAXIMIZE": direction = "MAXIMIZE"; break;
    default: throw new Error("Invalid scoring direction");
  }
  return {
    criterion_id: optionalText(raw.criterion_id), name: text(raw.name),
    weight: numeric(raw.weight), direction, source_field: text(raw.source_field),
    source_type: optionalText(raw.source_type), description: optionalText(raw.description),
    is_knockout: raw.is_knockout == null ? undefined : boolean(raw.is_knockout),
    knockout_threshold: raw.knockout_threshold == null ? null : numeric(raw.knockout_threshold),
    categorical_map: raw.categorical_map == null ? null : numbers(raw.categorical_map),
  };
}

export function readConfiguration(value: unknown): ScoringConfigurationResponse {
  const raw = object(value);
  const payload = raw.config_payload == null ? raw : object(raw.config_payload);
  const criteria = list(payload.criteria).map(readCriterion);
  if (!criteria.length) throw new Error("Invalid scoring configuration");
  return {
    id: text(raw.id), rfq_id: optionalText(raw.rfq_id), version: numeric(raw.version),
    name: optionalText(payload.name ?? raw.name), description: optionalText(payload.description ?? raw.description),
    criteria, missing_value_policy: optionalText(payload.missing_value_policy),
    tie_policy: optionalText(payload.tie_policy),
    is_active: raw.is_active == null ? undefined : boolean(raw.is_active),
    created_at: optionalText(raw.created_at),
  };
}

export function writeConfiguration(data: ScoringConfigurationCreate) {
  return {
    ...data, missing_value_policy: "block_scoring", tie_policy: "standard_competitive",
    criteria: data.criteria.map((criterion, index) => ({
      ...criterion,
      criterion_id: criterion.criterion_id || `criterion_${index + 1}`,
      source_type: criterion.source_type || (criterion.source_field.includes("lead_time")
        ? "lead_time" : criterion.source_field.includes("payment") ? "payment_terms" : "price"),
      direction: criterion.direction === "MINIMIZE" ? "lower_is_better" : "higher_is_better",
      is_knockout: criterion.is_knockout ?? (criterion.knockout_threshold != null),
    })),
  };
}

function readContribution(value: unknown): CriterionScoreBreakdown {
  const raw = object(value);
  const rawValue = raw.raw_value ?? null;
  if (rawValue !== null && typeof rawValue !== "number" && typeof rawValue !== "string") {
    throw new Error("Invalid scoring raw value");
  }
  return {
    ...raw, raw_value: rawValue,
    normalized_score: numeric(raw.normalized_score), weight: numeric(raw.weight),
    weighted_contribution: numeric(raw.weighted_contribution),
    cohort_min: optionalNumber(raw.min_value ?? raw.cohort_min),
    cohort_max: optionalNumber(raw.max_value ?? raw.cohort_max),
    knockout_applied: boolean(raw.is_knockout_applied ?? raw.knockout_applied ?? false),
    source_path: optionalText(raw.source_path), notes: optionalText(raw.notes || raw.formula_audit),
    exact_raw_value: optionalText(raw.exact_raw_value),
    exact_normalized_score: optionalText(raw.exact_normalized_score),
    exact_weighted_contribution: optionalText(raw.exact_weighted_contribution),
  };
}

export function readScores(value: unknown): SupplierScore[] {
  if (!Array.isArray(value)) throw new Error("Invalid scoring results");
  return list(value).map((item) => {
    const raw = object(item);
    const status = eligibility(raw.eligibility_status ?? raw.status);
    const breakdown: Record<string, CriterionScoreBreakdown> = {};
    if (raw.criteria_breakdown != null) {
      for (const contribution of list(raw.criteria_breakdown)) {
        const row = object(contribution);
        breakdown[text(row.criterion_name)] = readContribution(row);
      }
    } else {
      for (const [name, contribution] of Object.entries(object(raw.breakdown ?? {}))) {
        breakdown[name] = readContribution(contribution);
      }
    }
    return {
      ...raw, quotation_id: text(raw.quotation_id), supplier_name: text(raw.supplier_name),
      status, is_eligible: status === "eligible",
      composite_score: numeric(raw.total_score ?? raw.composite_score),
      rank: rank(raw.rank), exact_total_score: optionalText(raw.exact_total_score),
      knockout_reasons: list(raw.knockout_reasons ?? []).map(text), breakdown,
    };
  });
}

export function readRun(value: unknown): ScoringRunResponse {
  const raw = object(value);
  const results = raw.results_payload == null ? undefined : object(raw.results_payload);
  const scores = readScores(results ? results.suppliers : raw.scores);
  return {
    id: text(raw.id), rfq_id: optionalText(raw.rfq_id),
    configuration_id: optionalText(raw.configuration_id),
    scoring_configuration_id: optionalText(raw.configuration_id ?? raw.scoring_configuration_id),
    scoring_configuration_version: optionalNumber(raw.scoring_configuration_version),
    snapshot_id: optionalText(raw.snapshot_id),
    comparison_snapshot_id: text(raw.snapshot_id ?? raw.comparison_snapshot_id),
    comparison_snapshot_version: optionalNumber(raw.comparison_snapshot_version),
    comparison_snapshot_hash: optionalText(raw.comparison_snapshot_hash),
    run_number: optionalNumber(raw.run_number), name: optionalText(raw.name),
    notes: optionalText(raw.notes), created_at: optionalText(raw.created_at),
    provenance_hash: optionalText(raw.provenance_hash), results_payload: results,
    scores,
  };
}

export function readSimulation(value: unknown): SupplierScore[] {
  return readScores(Array.isArray(value) ? value : object(value).scores);
}

function readBreakeven(value: unknown): BreakevenResult | null {
  if (value == null) return null;
  const raw = object(value);
  const targetRank = rank(raw.target_rank);
  if (targetRank == null) throw new Error("Invalid scoring breakeven rank");
  return {
    target_supplier_id: text(raw.candidate_id ?? raw.target_supplier_id),
    target_supplier_name: text(raw.candidate_name ?? raw.target_supplier_name),
    target_rank: targetRank, current_rank: optionalNumber(raw.current_rank),
    current_score: optionalNumber(raw.current_score), required_score: optionalNumber(raw.required_score),
    incumbent_supplier_id: optionalText(raw.incumbent_supplier_id),
    incumbent_supplier_name: optionalText(raw.incumbent_supplier_name),
    current_price: optionalNumber(raw.current_price),
    required_price: raw.required_price == null ? null : numeric(raw.required_price),
    price_delta: optionalNumber(raw.delta_price ?? raw.price_delta) ?? null,
    percentage_reduction_needed: optionalNumber(raw.delta_pct ?? raw.percentage_reduction_needed) ?? null,
    is_feasible: boolean(raw.feasible ?? raw.is_feasible),
    bisection_iterations: optionalNumber(raw.convergence_steps ?? raw.bisection_iterations),
    explanation: optionalText(raw.notes ?? raw.explanation) ?? "",
  };
}

export function readSensitivity(value: unknown, request: SensitivityRequest): SensitivityResponse {
  const raw = object(value);
  return {
    comparison_snapshot_id: request.comparison_snapshot_id,
    sweep_criterion: text(raw.swept_criterion_id ?? raw.sweep_criterion),
    data_points: list(raw.points ?? raw.data_points).map((item) => {
      const point = object(item);
      return {
        weight: numeric(point.weight), weights_vector: numbers(point.redistributed_weights ?? point.weights_vector),
        supplier_scores: numbers(point.supplier_scores),
        ranks: Object.fromEntries(Object.entries(object(point.rankings ?? point.ranks)).map(([key, value]) => [
          key,
          // Older presentation payloads used zero for an unranked supplier.
          point.rankings == null && value === 0 ? null : rank(value),
        ])),
      };
    }),
    crossover_points: list(raw.crossover_points ?? []).map((item) => {
      const point = object(item);
      const supplierA = text(point.supplier_a ?? point.supplier_a_id);
      const supplierB = text(point.supplier_b ?? point.supplier_b_id);
      return {
        weight: numeric(point.weight), score_at_crossover: numeric(point.score_at_crossover),
        supplier_a_id: supplierA, supplier_b_id: supplierB,
        supplier_a_name: optionalText(point.supplier_a_name) ?? supplierA,
        supplier_b_name: optionalText(point.supplier_b_name) ?? supplierB,
        description: optionalText(point.description) ?? `${supplierA} / ${supplierB}`,
      };
    }),
    breakeven: readBreakeven(raw.breakeven),
  };
}
