# Security Policy

ProcureFlow is a technical preview. Use synthetic data for evaluation and review the deployment boundaries below before handling sensitive documents.

## Maintenance scope

Reports should identify the affected tag or commit and whether the issue also occurs on `main`. Fixes are evaluated on the current development branch; older tags do not have a separate long-term support commitment.

---

## Reporting a Vulnerability

**Do not publish vulnerability details in issues, pull requests, discussions, or comments.** Do not attach live credentials, customer data, or real supplier quotations.

Use GitHub's private **Report a vulnerability** form on the repository's [Security Advisories page](https://github.com/mbs20/procureflow/security/advisories). This requires the maintainer to enable private vulnerability reporting. If the button is unavailable, request that private reporting be enabled using a public issue containing only that request; do not include the affected component, reproduction, exploit, or impact until a private channel is available.

In the private report, include:

- Affected tag/commit, operating system, and deployment configuration, with secrets removed.
- Expected behavior, observed behavior, and a minimal synthetic reproduction.
- Potential impact and any suggested mitigation.
- A way to follow up and your preference for public credit.

Allow time for investigation and coordinate publication of details after a fix or mitigation is available. Response times depend on maintainer availability; there is no guaranteed response or remediation deadline. Only test systems you control or have permission to assess.

---

## Sensitive Data in ProcureFlow

- Never commit real supplier quotations or commercially confidential supplier contracts to the repository.
- Use the provided synthetic fixtures under [`backend/tests/fixtures/`](backend/tests/fixtures/) for test scenarios.

## MVP security boundaries

Protected operations use a single shared API-key principal. Events identify an access context, not a verified individual person or legal signature. Individual accountability requires future identity-provider integration; there are no individual accounts, roles or tenant isolation today.

The demo browser embeds the development key. Document preview/download routes do not provide individual access checks. Restrict the entire deployment behind an authenticated perimeter; do not expose the default Compose stack publicly or use its demonstration credentials for sensitive data. Changing only the backend key does not configure the browser clients.

General audit history is append-only by application convention, not a globally cryptographically chained ledger. Specific content/provenance hashes do not protect against privileged database changes. Restrict database access and test backups.

Remote interpretation can send quotation text to a provider; narratives send structured procurement context. Review provider retention and access policies before using sensitive data. See [scope and limitations](docs/LIMITATIONS.md).
