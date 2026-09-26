# Contributing to ProcureFlow

Bug reports, feature proposals, documentation changes, tests, and pull requests are welcome. ProcureFlow is an actively developed technical preview. Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) and report vulnerabilities privately through the [security policy](SECURITY.md).

## Choose a contribution

Check [existing issues](https://github.com/mbs20/procureflow/issues) before opening a report. Use the bug, feature, documentation, or extraction form. Include a reproducible example and use synthetic quotations; never publish credentials or confidential supplier data.

The [label guide](.github/LABELS.md) describes `good first issue`, `help wanted`, and topic labels. Labels are triage aids, not a promise that tasks are available. Discuss substantial changes in an issue before implementation. Documentation corrections and small fixes can go directly to a pull request.

## Fork and create a branch

1. Use **Fork** on [mbs20/procureflow](https://github.com/mbs20/procureflow).
2. Replace `YOUR_USERNAME` below with your GitHub username, then clone your fork:

```bash
git clone https://github.com/YOUR_USERNAME/procureflow.git
cd procureflow
git remote add upstream https://github.com/mbs20/procureflow.git
git fetch upstream
git switch -c docs/your-change upstream/main
```

Choose a descriptive branch such as `fix/csv-currency` or `docs/setup`. Keep each pull request focused and preserve unrelated work.

## Install and run

The [README quickstart](README.md#quickstart) runs the full Docker demo with synthetic data. For editing backend/frontend code, follow [local development](README.md#local-development-without-docker), including shell-specific activation and `backend/.env` settings.

From the repository root, install locked development dependencies:

```bash
cd backend
uv sync --frozen --extra dev
cd ../frontend
npm ci
```

Python 3.12 and Node.js 20 match CI. Backend tests use temporary SQLite databases, synchronous tasks, and mock providers; they do not need a running database, broker, or paid API. Runtime Docker tests do need the Compose services.

## Backend checks

From `backend/`:

```bash
uv run --no-sync ruff check src tests
uv run --no-sync ruff format --check src tests
uv run --no-sync mypy src/
uv run --no-sync pytest
```

To format touched Python files, use `uv run --no-sync ruff format path/to/file.py`. Avoid unrelated formatting changes. Add regression tests for changed behavior; documentation-only edits do not require artificial code tests.

For parser changes, run `uv run --no-sync python -m procureflow.scripts.evaluate_extraction` and consult the [evaluation boundaries](docs/EXTRACTION_EVALUATION.md). Provider-routing tests may select a remote provider with a simulated transport, but must not make paid requests.

For API schema changes, regenerate the tracked schema from `backend/` using `uv run --no-sync python -m procureflow.scripts.export_openapi`, review the diff, and run `uv run --no-sync pytest tests/unit/test_openapi_consistency.py`. Migration safety tests are part of the suite; do not reset an existing database to make a test pass.

## Frontend checks

From `frontend/`:

```bash
npm run typecheck
npm test
npm run build
```

There is currently no configured ESLint gate. TypeScript checking, Vitest, and the build are the existing frontend checks; do not treat type checking as a substitute for all lint rules.

## Browser and Docker tests

From the repository root, with Docker running:

```bash
docker compose up --build -d
docker compose ps
```

Wait for healthy backend/frontend services, then from `frontend/`:

```bash
npx playwright install chromium
npx playwright test
```

On Linux, use `npx playwright install --with-deps chromium`. Playwright starts Vite when port 5173 is free and a separate fixture server on 5174. Live Docker tests skip if the stack is unavailable; a skipped live test is not a passing integration check.

To run only the four live integration scenarios against the running stack:

```bash
npx playwright test 'e2e/docker_live_.*\.spec\.ts' --reporter=list
```

The expression above works in Bash and PowerShell; use double quotes in Windows Command Prompt. Stop the stack from the repository root with `docker compose down`. Do not add `-v` unless you intentionally want to delete its database and document volumes. Tests create synthetic RFQs; use a development instance.

## Documentation and final review

Preview changed Markdown, check relative links and heading anchors, and try setup commands in the documented shell. The repository has no dedicated Markdown/link-check command. From the repository root, run `git diff --check` and review `git diff` for secrets, confidential fixtures, temporary files, and unrelated changes.

The optional Makefile wraps the checks above using `uv run` and npm. GNU Make is not required; use the explicit commands on Windows if it is unavailable.

## Submit a pull request

```bash
git add path/to/changed-file
git commit -m "docs: clarify local setup"
git push -u origin docs/your-change
```

Open a pull request from your fork's branch to `mbs20/procureflow:main`. Describe the problem, the change, and how you verified it. Link a related issue if one exists, use the PR checklist, and state any checks you could not run. Keep commit messages descriptive. Respond to review feedback with focused follow-up commits. CI results and review determine whether a change is ready; opening a PR does not guarantee acceptance.
