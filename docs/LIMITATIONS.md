# ProcureFlow: scope and limitations

ProcureFlow is a self-hosted technical preview for evaluating quotation comparison with synthetic or suitably controlled data. The supplied Docker Compose stack is a development/demo deployment, not an internet-facing production configuration.

## Authentication and deployment

Protected operations validate a single shared API key (`X-API-Key` or Bearer header). Events identify a shared access context, not a verified individual buyer; some events have system or legacy labels. There are no individual accounts, roles, SSO or tenant boundaries. Award confirmation is an explicit API action intended for a buyer, but possession of a key does not prove a human initiated it. It is not a legally verified signature. Individual accountability requires future identity-provider integration.

The browser clients embed the development key. Changing the backend key alone does not configure the frontend. Document preview/download routes also lack individual access checks. Restrict access to the entire deployment behind an authenticated perimeter; do not expose the demo publicly.

`PROCUREFLOW_ENV=production` activates startup checks rejecting mock mode, debug mode, default API keys, short/default secret keys and wildcard CORS. Non-root images and these checks are not a complete security boundary. Compose still uses development credentials, published database/broker ports, bind mounts and backend reload.

## Event history and hashes

1. Application services append general `AuditLog` and award lifecycle events. The generic `audit_logs` table has no hash column or cryptographic chain. Privileged database access can modify it.
2. Specific artifacts have SHA-256 content/provenance hashes: documents, comparison snapshots, scoring configurations/runs, decision contexts, narrative inputs/outputs and confirmed awards. These support reproducibility and comparison with a trusted reference, not signatures or protection against database administrators.
3. There is no globally cryptographically chained audit ledger, external timestamp authority or write-once storage. Frozen records are retained by application convention; the underlying database is not physically immutable.

Operators remain responsible for database access controls and tested backups.

## Extraction and provider boundaries

- Supported uploads: PDF, CSV and `.xlsx`. Legacy `.xls` is rejected; convert it first.
- Recognizable tables use deterministic parsers. Other PDFs use the configured interpretation provider or explicit offline mock heuristics. OCR requires Tesseract. Poor scans and complex layouts can lose or misinterpret fields.
- Source evidence does not prove interpretation accuracy. Native text blocks have coordinates; table citations may lack bounding boxes, and OCR citations can cover a whole page.
- OpenAI, Anthropic and Ollama share explicit extraction/narrative routing. See [provider configuration](adr/0002-llm-abstraction-and-instructor.md). Tests simulate transports; they do not certify live models or structured-output quality. Configuration and provider failures are explicit errors, not silent mock results.
- The [extraction evaluation](EXTRACTION_EVALUATION.md) reports expected and observed fields on a small synthetic corpus, not general accuracy.
- Narrative grounding checks structured references and selected numeric claims, not every sentence. Buyers must review narrative content and source documents.

## Other limitations

- Scoring is deterministic for fixed snapshot, configuration and engine policy. This does not establish source-data accuracy or suitability of chosen weights.
- Local filesystem storage only; remote object storage is not implemented.
- Exchange rates are configured snapshots; demonstration rates are synthetic. No live FX feed or ERP/P2P connector is connected.
- UI localization supports English and French; generated narratives currently remain in English.
- Playwright/Axe checks cover selected scenarios, not complete WCAG conformance or a manual accessibility audit.

Use synthetic documents for evaluation. For a controlled pilot, review the access boundaries, terminate TLS at the perimeter, restrict database/broker access and test restoration. See [security](../SECURITY.md) and [troubleshooting](TROUBLESHOOTING.md).
