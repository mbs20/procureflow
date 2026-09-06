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
