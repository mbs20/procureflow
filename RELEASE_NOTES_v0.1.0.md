# Release Notes — ProcureFlow OSS v0.1.0 (Technical Preview)

> **Release Tag**: `v0.1.0`  
> **Release Target**: Open-Source Technical Preview / Self-Hosted MVP

ProcureFlow OSS v0.1.0 is the initial public technical preview release of ProcureFlow, an open-source, AI-assisted RFQ comparison and evidence-grounded procurement decision platform.

---

## 🌟 Key Highlights

- **Multi-Format Quotation Ingestion**: Ingest PDF, Excel (`.xlsx`), and CSV supplier quotations.
- **Deterministic Field Extraction & Verification**: Structured line-item, commercial term, and currency extraction with source bounding box and line citations.
- **Split-Pane Human Review Workspace**: Side-by-side verification allowing procurement officers to click extracted numbers and immediately highlight their exact coordinates on the source document.
- **Multi-Supplier Comparison & Normalization**: Cross-supplier side-by-side matrices with synthetic currency normalization and standardized units.
- **Deterministic Linear Scoring & Knockout Rules**: Mathematically reproducible weighted scoring, parameter sweeps, and mandatory eligibility criteria.
- **Immutable Decision Context & Grounded Narrative**: AI-generated decision memos where every quantitative claim is grounded in immutable, pre-computed structured facts.
- **Human Award Workflow**: Complete award lifecycle requiring explicit buyer authorization, mandatory rationale for non-top-ranked awards, and superseded warnings when underlying data updates.
- **True One-Command Demo**: Spin up the entire pre-seeded stack with `docker compose --profile demo up --build`.

---

## 🛡️ Production Hardening Included

- **Non-Root Containers**: Backend runs as `appuser` (UID 10001); frontend runs as unprivileged `nginx` (UID 101).
- **Strict Startup Configuration Invariants**: Production mode rejects development secrets, short keys (<32 chars), default API keys, wildcard CORS, and mock LLM settings.
- **Migration Safety Gates**: Chained Alembic migrations with automated test gates validating both blank database fresh-installs and upgrade-path schema integrity without data loss.
- **Idempotent & Non-Destructive Seed**: Safe, synthetic demonstration data that can be run repeatedly without duplicating records or clobbering user data.
- **Static OpenAPI 3.1.0 Schema**: Fully documented and CI-verified against FastAPI route registration.
- **Accessibility Verification**: Automated WCAG 2.2 AA accessibility checks via Playwright + Axe.

---

## ⚠️ Known Limitations

v0.1.0 is designed for self-hosted evaluation and single-organization deployment. Current architectural limitations:
- Single-tenant organization model (no multi-tenant isolation or RBAC roles).
- Local filesystem document storage (cloud S3/GCS drivers planned for v0.2.0).
- Synthetic fixed demonstration FX rates (1 EUR = 1.08 USD) rather than real-time financial market feeds.
- No direct live ERP connectors (SAP/Coupa/NetSuite); structured data is accessible via REST API.

See [LIMITATIONS.md](docs/LIMITATIONS.md) for detailed deployment guidance.
