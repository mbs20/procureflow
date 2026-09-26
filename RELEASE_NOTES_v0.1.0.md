# Release Notes — ProcureFlow OSS v0.1.0 (Technical Preview)

> **Release Tag**: `v0.1.0`  
> **Release Target**: Open-Source Technical Preview / Self-Hosted MVP

ProcureFlow OSS v0.1.0 is the initial public technical preview release of ProcureFlow, an open-source RFQ comparison and evidence-grounded procurement decision platform.

These notes describe the v0.1.0 preview; the current branch includes later fixes. See the [README](README.md) for current setup and the [limitations](docs/LIMITATIONS.md) for present boundaries. Planned work is not shipped functionality.

---

## Key Capabilities

- **Multi-Format Quotation Ingestion**: Ingest PDF, Excel (`.xlsx`), and CSV supplier quotations.
- **Field Extraction & Verification**: Structured line-item, commercial term, and currency extraction with source bounding box and line citations.
- **Split-Pane Human Review Workspace**: Side-by-side inspection of extracted values and available source citations. Table citations may lack bounding boxes; OCR citations may cover a whole page.
- **Multi-Supplier Comparison & Normalization**: Cross-supplier side-by-side matrices with synthetic currency normalization and standardized units.
- **Deterministic Linear Scoring & Knockout Rules**: Mathematically reproducible weighted scoring, parameter sweeps, and mandatory eligibility criteria.
- **Retained Decision Context & Narrative Assistance**: Draft memos reference stored evaluation facts. Structured checks cover selected claims; they do not verify every sentence or eliminate interpretation errors.
- **Human Award Workflow**: Complete award lifecycle requiring explicit buyer authorization, mandatory rationale for non-top-ranked awards, and superseded warnings when underlying data updates.
- **Docker Demo**: With Docker and Compose installed and running, start the pre-seeded stack with `docker compose --profile demo up --build`.

---

## Deployment Controls and Validation

- **Non-Root Containers**: Backend runs as `appuser` (UID 10001); frontend runs as unprivileged `nginx` (UID 101).
- **Strict Startup Configuration Invariants**: Production mode rejects development secrets, short secret keys (<32 chars), default API keys, wildcard CORS, and mock LLM settings.
- **Migration Checks**: Tests migrate an empty SQLite database to Alembic head and validate schema drift. A separate test inserts an RFQ after migration, repeats `upgrade head`, and verifies that the record is preserved. This checks idempotence, not migration from an older populated database revision. Back up data before upgrades.
- **Idempotent & Non-Destructive Seed**: Safe, synthetic demonstration data that can be run repeatedly without duplicating records or clobbering user data.
- **Static OpenAPI Schema**: A tracked schema checked against FastAPI output in the test suite.
- **Accessibility Verification**: Selected Playwright + Axe checks; these do not certify complete WCAG conformance.

---

## Known Limitations

v0.1.0 is designed for local self-hosted evaluation with synthetic data. The supplied stack is not a hardened production deployment. Architectural limitations (see the linked scope document for current boundaries):
- Shared API-key access without individual accounts, organization management, multi-tenant isolation, or RBAC roles.
- Local filesystem document storage (cloud storage remains roadmap work).
- Synthetic fixed demonstration FX rates (1 EUR = 1.08 USD) rather than real-time financial market feeds.
- No direct live ERP connectors (SAP/Coupa/NetSuite); structured data is accessible via REST API.

See [LIMITATIONS.md](docs/LIMITATIONS.md) for detailed deployment guidance.

The API-key model identifies a shared principal, not a verified individual human signature. The generic audit log is application-level history without a cryptographic chain; hashes protect references to specific artifacts only when compared with a trusted copy.
