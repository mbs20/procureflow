# ProcureFlow roadmap

ProcureFlow is a technical preview under active development. This roadmap separates existing capabilities from possible future work; it is not a release schedule or a commitment to implement every proposal.

## Implemented today

- Local Docker demo with synthetic RFQs and quotations.
- PDF, CSV, and XLSX ingestion, extraction review, and available source citations.
- Comparison snapshots, configured currency/unit normalization, deterministic scoring, and sensitivity analysis.
- Draft narratives, explicit award confirmation, and application event history.
- Mock, OpenAI, Anthropic, and Ollama routing; remote transports are covered by simulated tests, not a live compatibility certification.

See the [README](../README.md) for setup and [limitations](LIMITATIONS.md) for deployment and evidence boundaries.

## Candidate next steps

These need scoped proposals and validation before implementation:

- Broader synthetic extraction fixtures, including degraded scans and multilingual layouts.
- Clearer representation of missing prices and other ambiguous extracted values.
- Dependency maintenance, smaller frontend bundles, and expanded accessibility checks.
- Object storage and controlled document delivery.
- Live exchange-rate sources with reproducible snapshots.
- Documented export formats and selected ERP integrations.
- Individual authentication, permissions, and tenant isolation if supported deployment needs justify them.
- Broader local-model compatibility, potentially including vLLM or vision-based parsing.

Storage integrations, live financial feeds, ERP connectors, SSO/RBAC, tenant isolation, and signed decision documents are not implemented today. They must not be inferred from example data or architecture proposals.

## Propose work

Open a feature request describing the user problem, a bounded scope, and how the result could be tested. Follow [CONTRIBUTING.md](../CONTRIBUTING.md). A proposal or roadmap entry is not an accepted implementation plan.
