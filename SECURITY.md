# Security Policy

ProcureFlow OSS takes security, data privacy, and the integrity of commercial procurement data seriously.

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

---

## Reporting a Vulnerability

If you discover a security vulnerability in ProcureFlow OSS:
1. **Do not create a public GitHub issue.**
2. Send an email to the maintainer or open a private GitHub Security Advisory at [https://github.com/mbs20/procureflow/security/advisories](https://github.com/mbs20/procureflow/security/advisories).
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested mitigation if available

We will acknowledge receipt of your report within 48 hours and work with you to coordinate a responsible disclosure and patch.

---

## Sensitive Data in ProcureFlow

- Never commit real supplier quotations or commercially confidential supplier contracts to the repository.
- Use the provided synthetic fixtures under `tests/fixtures/` for test scenarios.

## MVP security boundaries

Protected operations use a single shared API-key principal. Events identify an access context, not a verified individual person or legal signature. Individual accountability requires future identity-provider integration; there are no individual accounts, roles or tenant isolation today.

The demo browser embeds the development key. Document preview/download routes do not provide individual access checks. Restrict the entire deployment behind an authenticated perimeter; do not expose the default Compose stack publicly or use its demonstration credentials for sensitive data. Changing only the backend key does not configure the browser clients.

General audit history is append-only by application convention, not a globally cryptographically chained ledger. Specific content/provenance hashes do not protect against privileged database changes. Restrict database access and test backups.

Remote interpretation can send quotation text to a provider; narratives send structured procurement context. Review provider retention and access policies before using sensitive data. See [scope and limitations](docs/LIMITATIONS.md).
