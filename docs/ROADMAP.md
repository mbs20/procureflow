# ProcureFlow OSS — Roadmap

This roadmap outlines anticipated capabilities and architectural evolutions planned for post-v0.1.0 releases.

---

## 🧭 Milestone Summary

```
v0.1.0 (Current)             v0.2.0 (Q4 2026)             v0.3.0 (Q1 2027)
[Technical Preview]   ──►    [Cloud & Integrations] ──►   [Enterprise Multi-Tenant]
- Self-hosted MVP            - S3/GCS Object Storage       - Organization isolation
- 1-command Docker demo      - Live FX feeds (ECB/Oanda)   - SAML 2.0 / OIDC SSO
- Document citation engine   - Bidirectional ERP exports   - Role-Based Access Control
- Grounded decision memos    - Multi-line RFP clustering   - Signed PDF Decision Briefs
```

---

## 📦 Planned Capabilities

### 1. Storage & Cloud Drivers (v0.2.0)
- **S3-Compatible Object Storage**: Replace local filesystem storage with S3, Google Cloud Storage, and Azure Blob drivers.
- **Signed URL Document Streaming**: Secure time-limited document preview URLs for browser PDF rendering.

### 2. Market Data & Financial Feeds (v0.2.0)
- **Live FX Synchronization**: Automated daily exchange rate sync via European Central Bank (ECB) or Open Exchange Rates API.
- **Inflation & Commodity Indexing**: Benchmark raw material price changes against commodity indices (e.g., LME steel/nickel).

### 3. ERP & P2P Ecosystem (v0.2.0 - v0.3.0)
- **Standardized Export Schemas**: Export ComparisonSnapshots and Award Decisions in standard formats (cXML, PEPPOL, JSON-LD).
- **ERP Webhook Connectors**: Webhooks notifying external ERPs (SAP, NetSuite, Coupa) upon human award confirmation.

### 4. Enterprise Identity & Multi-Tenancy (v0.3.0)
- **Tenant Isolation**: Row-level security (RLS) or schema-per-tenant isolation for SaaS hosting.
- **Enterprise SSO**: OIDC and SAML 2.0 integration (Okta, Azure AD / Microsoft Entra ID).
- **Fine-Grained RBAC**: Distinct permissions for Category Managers, Compliance Reviewers, and Executives.

### 5. Advanced Model Support & Local Inference (v0.3.0)
- **Local LLM Drivers**: Broader local-model compatibility testing and vLLM integration. Ollama routing exists; structured-output quality depends on the selected model.
- **Vision-Language Document Parsing**: End-to-end multi-modal vision parsing for intricate engineering drawings and blueprints.
