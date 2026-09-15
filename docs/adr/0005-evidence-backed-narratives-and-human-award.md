# ADR 0005: Evidence-Backed Decision Narratives and Human-in-the-Loop Award Workflow

## Status
Accepted

## Context
In Phase 6, ProcureFlow introduces AI narrative generation to assist procurement officers in summarizing, comparing, and drafting decision memos for complex evaluations. However, LLMs are prone to hallucinating facts, misquoting numbers, and inventing vendor advantages. Furthermore, public sector and enterprise procurement regulations strictly forbid automated awarding: a human buyer must retain sole authority and accountability for vendor selection.

A strict architectural separation is required between deterministic procurement facts (Phases 1–5), advisory AI narrative synthesis, and the human award confirmation lifecycle.

## Decision

1. **Immutable DecisionContext Artifact**:
   Prior to narrative generation, the system constructs and persists an immutable `DecisionContext` containing canonical structured data: RFQ metadata, `ComparisonSnapshot` ID/hash, `ScoringConfiguration` ID/hash, `ScoringRun` ID/provenance hash, deterministic supplier ranks and exact scores, criteria breakdowns, knockout states, warnings, and an integrity hash (`context_hash`). LLMs receive only this frozen context.

2. **Server-Side Rendered Numeric Claims & Grounding Validation**:
   Critical numeric values (total scores, ranks, normalized scores) are rendered server-side from `DecisionContext` rather than generated freely by LLMs. Generated claims are parsed into structured `NarrativeClaim` records referencing authoritative context fields. Post-generation grounding validation deterministically flags any claim referencing unknown suppliers, invalid criteria, or mismatched scores/ranks as `unsupported`.

3. **Strict Architectural Separation (No Autonomous Awards)**:
   `NarrativeService` and LLM providers have zero access, permissions, or code pathways to award an RFQ or mutate procurement decisions. The LLM is strictly advisory.

4. **Event-Sourced Award Lifecycle with Operational Projection**:
   All award actions are recorded as append-only `AwardDecisionEvent` entries (`DRAFT_CREATED`, `CONFIRMED`, `REVOKED`) with actor principals, timestamps, and payload snapshots. `AwardDecision` maintains the current projected operational state (`draft`, `confirmed`, `revoked`).

5. **Human Authority & Justification Guardrails**:
   - Only an authenticated human buyer can transition an award from `draft` to `confirmed`.
   - Selecting any supplier other than Rank #1 strictly requires a non-empty `non_rank1_rationale`.
   - Knockout-failed suppliers cannot be awarded under any circumstances (enforced at API and domain level).
   - Only one confirmed award may exist per RFQ at any time (double-award conflict rejected with 409).
   - Confirmation transitions RFQ status to `DECIDED`; revocation reverts RFQ status to `EVALUATING` and records an immutable revocation event.

6. **Append-Only Human Narrative Revisions & Superseded Tracking**:
   Narratives support append-only human revisions (`NarrativeRevision`). When a new `ScoringRun` is executed, previous narratives are marked as `is_superseded` with explicit audit reasons.

## Consequences
- **Positive**: 100% auditable, grounded, and legally defensible narratives; eliminates autonomous award risks; full event-sourced lineage with SHA-256 provenance binding.
- **Negative**: Adds database artifacts (`DecisionContext`, `AwardDecisionEvent`, `NarrativeClaim`) and validation steps before presenting AI narratives.
