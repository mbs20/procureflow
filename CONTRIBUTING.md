# Contributing to ProcureFlow OSS

Thank you for your interest in contributing to ProcureFlow OSS! As an open-source project, we value transparency, clean engineering, testability, and a constructive community.

---

## 🧭 Code of Conduct

All contributors are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please report any unacceptable behavior to the project maintainer.

---

## 🛠️ Development Workflow

### Branching Strategy
- Branch from `main`
- Name branches descriptively:
  - `feat/add-new-parser`
  - `fix/scoring-rounding-issue`
  - `docs/update-adr-0002`
  - `test/add-csv-fixtures`

### Conventional Commits
We enforce [Conventional Commits](https://www.conventionalcommits.org/) for automated semantic releases:
- `feat: add PDF bounding box citation mapping`
- `fix: correct negative currency conversion error`
- `docs: add instructions for local Ollama usage`
- `test: add sample quotations fixture suite`
- `refactor: extract scoring strategy interface`

---

## 🧪 Testing Guidelines

Before opening a Pull Request:
1. **Never mock away domain logic**: Normalisation, scoring calculations, and parsers must have unit tests covering edge cases.
2. **Deterministic LLM tests**: Tests interacting with LLM abstractions must run offline against pre-recorded fixtures or mock providers.
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

## 🧩 Adding New Extensible Components

### 1. Adding a Document Parser
Implement the `BaseParser` interface located in `backend/src/procureflow/ingestion/parsers/base.py`. Ensure your parser returns standard text chunks with page or line coordinates.

### 2. Adding a Scoring Strategy
Implement the `ScoringStrategy` protocol located in `backend/src/procureflow/scoring/strategies/base.py`. Ensure your strategy is deterministic and outputs granular breakdown items.

### 3. Adding an LLM Provider
Add your provider integration into `backend/src/procureflow/ai/client.py` using standard LiteLLM configuration parameters.

---

## 📬 Submitting Pull Requests

1. Ensure all tests pass.
2. Update relevant documentation or ADRs if proposing architectural changes.
3. Use the PR template and link any relevant GitHub Issues.
4. Maintainers will review your PR and provide actionable feedback.
