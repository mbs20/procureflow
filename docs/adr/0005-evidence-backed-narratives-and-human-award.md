# ADR 0005: Evidence-backed narratives and explicit award confirmation

## Status
Accepted

## Context
Buyers need memos linked to evaluation facts. Generated text can contain unsupported interpretations, so narrative generation remains separate from ranking and confirmation.

## Decision
- `DecisionContext` retains RFQ, snapshot, configuration and scoring-run references, evaluation facts and a content hash. Normal operations preserve the context rather than overwrite it.
- Narrative generation uses a provider projection. Structured validation checks references and selected numeric facts and marks unsupported/unverifiable claims. It does not verify every free-text assertion.
- Narrative providers have no tool interface for awarding suppliers. `AwardService` does not invoke them. Buyers can confirm awards without generating narratives.
- Draft, confirmation and revocation events are appended to `AwardDecisionEvent`; `AwardDecision` stores current state. Non-first-ranked selection requires justification, ineligible suppliers are rejected and concurrent confirmed awards are prevented.
- Confirmation requires an authenticated API request intended for a buyer. The shared API-key principal does not verify individual human identity; software holding the key can also call the API. Stronger accountability requires future identity-provider integration.
- Narrative revisions are appended and superseded narratives carry warnings.

## Integrity boundaries
SHA-256 hashes bind specific contexts, narrative templates/inputs/outputs and confirmed awards to their recorded content. They are not signatures, a global event chain or protection against privileged database modification. General `AuditLog` records are not cryptographically chained. These mechanisms do not certify legal compliance.

## Consequences
Facts, provider output and decisions remain separately inspectable. Buyers must review source documents and narratives. Operators must protect database access, backups, credentials and the deployment perimeter.
