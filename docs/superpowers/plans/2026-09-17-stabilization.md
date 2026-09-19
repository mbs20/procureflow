# ProcureFlow v0.1.1 stabilization plan

Goal: repair confirmed audit defects without changing scoring mathematics or human authority.
Baseline: main 1548b5695f844e3e38a73d64c0a13324983fb5a0.
Branch: fix/v0.1.1-stabilization. No manual browser sessions, volume deletion, database reset, tag or merge.

- [x] Forms/review: reproduce native step mismatch and unsafe numeric handling; strict validation and regression tests. Diagnose PDF worker against production HTTP.
- [x] Ingestion: atomic document/quotation persistence; integration coverage for failed upload/retry; generic PDF plausibility and evidence preservation.
- [x] Trust: approved current extraction filtering; authoritative narrative cohort validation; complete award history.
- [x] Scoring: adapt actual API schema to UI, enforce prerequisites, localize actionable errors; realistic payload regression coverage.
- [x] Confirmed P1: source download, CSV export, effective lead time, global audit data, responsive navigation, worker health and runtime DNS.
- [x] Integration: synthetic API-to-award regression without bypassing extraction/scoring logic; bilingual coverage.
- [x] Gates: full pytest, frontend unit/typecheck/build, Playwright/accessibility, migrations, Docker/live checks. Review changes, logical commits, push only when gates pass.

Implementation boundaries: forms agent owns RFQ/review dialogs and PDFViewer; ingestion agent owns quotation persistence/parsing and upload page; trust agent owns comparison/decision backend. Coordinator owns scoring frontend, runtime, locales, matrix UI/global audit and final integration. Shared files require coordination.

Final gates: 150 backend tests in Docker plus the OpenAPI test on host; 51 frontend tests; typecheck/build; 41 Playwright scenarios including all four Docker live suites pass. Production PDF/CSV/source navigation, append-only award history, PostgreSQL Alembic head/check, worker health and backend recreation without frontend restart verified. See docs/stabilization-v0.1.1-report.md.
