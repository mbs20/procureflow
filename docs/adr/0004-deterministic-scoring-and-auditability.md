# ADR 0004: Deterministic scoring and application history

## Status
Accepted

## Context
Rankings must be reproducible from explicit inputs and weights. Generated narratives are not authoritative scores or award instructions.

## Decision
1. Scoring uses a weighted sum of normalized criteria, with explicit eligibility, missing-value and tie policies. Full decimal precision determines rank; rounded values are for display.
2. `ScoringRun.results_payload` retains supplier contributions and formula details. Snapshot/configuration hashes contribute to run provenance. Fixed inputs and engine policy produce reproducible results.
3. Interpretation and narrative providers are separate from scoring. Narrative content requires review against source evidence.
4. Normal RFQ deletion archives the RFQ. Explicit demo reset and database administration are outside this archival guarantee.
5. Services append `audit_logs` records. This is application history, not a cryptographic chain or protection against privileged database changes. Specific provenance hashes do not protect the entire journal.

## Consequences
The design supports inspection, regression tests and retained history. It does not certify regulatory compliance, correctness of criteria or individual human identity. See [scope and limitations](../LIMITATIONS.md).
