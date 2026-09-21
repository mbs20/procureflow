# Contributing to ProcureFlow

Thank you for your interest in contributing to ProcureFlow. Contributions that improve code clarity, test coverage, and documentation are welcome.

---

## Code of Conduct

All contributors are expected to follow the [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainer.

---

## Development Workflow

### Branching Strategy
- Branch from `main`.
- Use descriptive branch names:
  - `feat/add-new-parser`
  - `fix/scoring-rounding-issue`
  - `docs/update-adr-0002`
  - `test/add-csv-fixtures`

### Commit Conventions
Commits follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat: add PDF bounding box citation mapping`
- `fix: correct currency conversion rounding`
- `docs: update local development guide`
- `test: add sample quotations fixture suite`
- `refactor: extract scoring strategy interface`

---

## Testing Guidelines

Before opening a Pull Request:

1. **Domain logic testing**: Normalization routines, scoring calculations, and document parsers must have unit tests covering typical inputs and edge cases.
2. **Offline test execution**: Tests interacting with narrative summary components must run offline against pre-recorded fixtures or mock providers.
3. **Format and lint**:
   ```bash
   # Python
   ruff check backend/
   ruff format --check backend/
   mypy backend/src/

   # TypeScript
   npm --prefix frontend run lint
   npm --prefix frontend run typecheck
   ```
4. **Run the test suite**:
   ```bash
   pytest backend/tests/
   ```

---

## Adding Extensible Components

### 1. Document Parsers
Implement the `BaseParser` interface in `backend/src/procureflow/ingestion/parsers/base.py`. Parsers should extract tabular line items with page numbers and spatial coordinates where possible.

### 2. Scoring Strategies
Implement the `ScoringStrategy` protocol in `backend/src/procureflow/scoring/strategies/base.py`. Scoring logic must remain deterministic and provide a granular breakdown of each criterion score.

### 3. Narrative Providers
Add provider integrations into `backend/src/procureflow/ai/client.py` using standard configuration parameters.

---

## Submitting Pull Requests

1. Ensure the backend and frontend test suites pass cleanly.
2. Update relevant documentation or ADRs if proposing architectural changes.
3. Use the pull request template and link any relevant issues.
4. Pull requests are reviewed by the maintainer with constructive feedback.
