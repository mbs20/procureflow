# ProcureFlow OSS — Limitations & Production Hardening Scope

> **Release Positioning**: ProcureFlow v0.1.0 is an **open-source technical preview and self-hosted MVP**. It demonstrates end-to-end, evidence-grounded quotation ingestion, multi-currency normalization, deterministic scoring, and human-in-the-loop decision-support. It is not an unconditional enterprise production claim for multi-tenant SaaS.

---

## 🛡️ Production Hardening Performed in v0.1.0

The following hardening measures have been implemented and verified in the v0.1.0 codebase:

| Hardening Domain | Implemented Controls |
| :--- | :--- |
| **Container Security** | Backend runs as non-root user `appuser` (UID 10001); frontend served via unprivileged Nginx (`nginxinc/nginx-unprivileged:alpine`, UID 101). |
| **Startup Config Guardrails** | In `ENVIRONMENT=production`, startup crashes immediately if default development `SECRET_KEY`, short keys (<32 chars), default `API_KEY`, wildcard CORS `["*"]`, `DEBUG=True`, or `PROCUREFLOW_LLM_PROVIDER=mock` are configured. |
| **Database Migration Safety** | Chained Alembic migrations with automated CI tests validating both fresh-install (`alembic upgrade head` on blank DB) and upgrade-path schema integrity without dropping historical tables. Zero schema drift (`alembic check`). |
| **Deterministic Data Isolation** | Demo dataset is synthetic, deterministic, and idempotent. The `--reset` command is strictly scoped to `[DEMO]`-prefixed records and never deletes user-created RFQs or quotations. |
| **API Contract Integrity** | Static OpenAPI 3.1.0 specification generated reproducibly via script and verified against FastAPI route registration in CI to prevent schema drift. |
| **Network & Service Health** | HTTP healthchecks on backend (`/api/v1/health`), Redis (`redis-cli ping`), and PostgreSQL (`pg_isready`). Frontend reverses `/api/` traffic to the backend over internal Docker networking with security headers (`X-Frame-Options`, `X-Content-Type-Options`). |
| **Audit Immutability** | Append-only audit log records every quotation status change, field override, and award event with SHA-256 integrity verification. |

---

## ⚠️ Current Architecture Limitations

While hardened for self-hosted evaluation and pilot procurement workflows, v0.1.0 has the following architectural limitations:

### 1. Tenancy & Authentication
- **Single-Tenant Scope**: v0.1.0 is designed for single-organization or private internal deployment. It does not enforce multi-tenant database isolation or role-based access control (RBAC) tiers (e.g., Buyer vs. Auditor roles).
- **API Key Protection**: Authentication relies on header-based API key validation (`X-API-Key`). Enterprise Single Sign-On (SSO / SAML 2.0 / OIDC) is not yet implemented.

### 2. Document Storage Backend
- **Local Filesystem Only**: Uploaded quotation documents are currently stored in the configured local directory (`UPLOAD_DIR`). Distributed cloud object stores (e.g., AWS S3, Google Cloud Storage, Azure Blob) are abstracted in the architecture but not yet wired to a remote cloud driver.

### 3. FX Normalization & Live Rates
- **Fixed Synthetic Rates**: Ingestion normalizes currencies into base RFQ currency using a synthetic fixed demonstration exchange rate (e.g., 1 EUR = 1.08 USD). ProcureFlow does not connect to live market FX feeds or financial oracle APIs.

### 4. LLM Providers & Ingestion Scale
- **Supported Providers**: Structured quotation extraction and decision memos support OpenAI (`gpt-4o`, `gpt-4o-mini`), Anthropic (`claude-3-5-sonnet`), and a deterministic offline `mock` provider. Open-source local models (vLLM / Ollama) require custom endpoint configuration.
- **Complex Table Parsing**: Scanned multi-page PDF tables with non-standard merged cells or handwritten notes require human review via the split-pane verification workspace.

### 5. Enterprise Integrations
- **No Direct ERP/P2P Sync**: v0.1.0 does not include live bidirectional synchronization connectors for SAP Ariba, Coupa, or Oracle Cloud Procurement. Comparison snapshots and awarded decisions can be exported via JSON API.

---

## 📋 Recommended Deployment Posture

For evaluation or self-hosted deployment:
1. Deploy behind a secure reverse proxy (e.g., Traefik, Caddy, or AWS ALB) terminating TLS/HTTPS.
2. Store persistent database volumes (`postgres_data`) on redundant, backed-up storage.
3. Set `ENVIRONMENT=production` and generate cryptographically secure keys:
   ```bash
   openssl rand -hex 32
   ```
4. Configure an outbound LLM API key (`OPENAI_API_KEY` or `ANTHROPIC_API_KEY`) if you wish to run extraction and decision narratives beyond the deterministic mock engine.
