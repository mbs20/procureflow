# Contributing to ProcureFlow

Contributions, suggestions, and bug reports are welcome. Whether improving parser heuristics, fixing a typo, or adding test cases, help is appreciated.

---

## Getting Started

1. Fork the repository and create a feature or fix branch from `main`.
2. Keep commit messages concise and descriptive (for example using prefixes like `feat:`, `fix:`, or `docs:`).

---

## Running Checks Locally

Before opening a pull request, you can run tests and linters locally:

```bash
# Backend checks
cd backend
ruff check .
ruff format --check .
mypy src/
pytest

# Frontend checks
cd ../frontend
npm run typecheck
npm test
```

When contributing new parsers or scoring adjustments, adding a unit test with sample inputs helps prevent regressions. Tests that interact with language model wrappers should use the offline mock provider (`PROCUREFLOW_LLM_PROVIDER=mock`) so they run quickly without API keys.

---

## Opening a Pull Request

Push your branch to your fork and open a pull request against `main`. Feel free to include a short note on what was changed and why.
