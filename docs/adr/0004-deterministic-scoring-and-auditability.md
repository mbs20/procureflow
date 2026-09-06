# ADR 0004: Deterministic Scoring Engine, Soft Deletion, and Auditability

## Status
Accepted

## Context
A major pitfall of naive AI procurement software is treating vendor evaluation as an LLM "prompt-and-answer" exercise. LLM-based scoring is non-deterministic, hallucinatory, opaque to auditors, and impossible to defend under legal scrutiny. Procurement compliance mandates complete explainability: every decimal point of a supplier's score must be traceable to underlying data points and explicit criteria weights.

Furthermore, procurement records must maintain an audit trail; hard deletion of sourcing events destroys corporate institutional memory and compliance records.

## Decision
1. **Deterministic Linear Weighted Scoring**:
   The core scoring engine is purely deterministic code with zero LLM involvement. Scores are computed as `Σ (normalised_criterion_value × weight)`.
2. **Explicit Score Breakdown Storage**:
   Every computation persists a granular `score_result` containing per-supplier, per-criterion contribution values, and snapshots of currency conversion rates.
3. **AI Confined to Guidance**:
   LLMs are strictly confined to generating plain-English explanatory narratives of the calculated scores. This narrative is visibly marked as "AI-generated advisory" and can be reviewed or edited by human evaluators.
4. **Soft Deletion / Archival Policy**:
   RFQs and associated procurement documents are never permanently destroyed in standard operations. An `is_archived` / `status=archived` mechanism preserves historical records and associated audit logs.
5. **Append-Only Audit Log**:
   All state transitions, extraction revisions, score recalculations, and decision justifications are recorded in an append-only `audit_log` table.

## Consequences
- **Positive**: 100% auditable, defendable, and testable scoring logic; compliant with procurement standards; historical continuity.
- **Negative**: Requires careful indexing of archived records to ensure active listing queries remain fast.
