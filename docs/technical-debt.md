# Dependency maintenance

The repository locks Python dependencies in `backend/uv.lock` and frontend dependencies in `frontend/package-lock.json`. Use `uv sync --frozen --extra dev` from `backend/` and `npm ci` from `frontend/` to reproduce them.

A previous dependency review is not evidence that the current tree is vulnerability-free. To inspect current frontend advisories, run from `frontend/`:

```bash
npm audit
```

This command queries the package registry and may return a nonzero exit code for known advisories. Assess each advisory against the installed version and the application's actual usage. A client-side SPA can still have vulnerable build-time or browser dependencies; the absence of server-side rendering is not a blanket exemption.

Do not run `npm audit fix --force` without reviewing the resulting major upgrades. Keep dependency changes focused, review both manifest and lockfile diffs, and run the [existing checks](../CONTRIBUTING.md). Framework upgrades can change routing, build configuration, or chart behavior and deserve separate regression coverage.

The frontend build currently warns about a large JavaScript bundle. Bundle size, broader accessibility coverage, and dependency upgrades are maintenance work, not claims of production readiness. For private vulnerability reports, follow [SECURITY.md](../SECURITY.md).
