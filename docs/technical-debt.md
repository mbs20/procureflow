# Technical Debt Note: Frontend Dependencies & Security Review

**Date**: 2026-09-06  
**Status**: Documented / Deferred Post-MVP  

---

## 1. Installed Package Versions Audit

The exact installed package versions in `frontend/node_modules` were audited:

| Package | Installed Version | Current Semver Constraint |
|---|---|---|
| `react-router` | `6.30.6` | Transitive (`react-router-dom@6.30.6`) |
| `react-router-dom` | `6.30.6` | `^6.27.0` |
| `vite` | `5.4.21` | `^5.4.9` |
| `esbuild` | `0.21.5` | Transitive (`vite@5.4.21`) |
| `recharts` | `2.15.4` | `^2.13.0` |

---

## 2. Security Advisories Summary

`npm audit` reports the following security advisories:

1. **esbuild / vite**:
   - **Advisory**: [GHSA-67mh-4wv8-2f99](https://github.com/advisories/GHSA-67mh-4wv8-2f99) (Moderate)
   - **Description**: Allows unauthorized cross-origin requests to local development server under specific origin configurations.
   - **Resolution via `--force`**: Bumps `vite` to `8.x`, introducing breaking changes to build plugins, configuration schemas, and dev server lifecycle.

2. **react-router / react-router-dom**:
   - **Advisories**: 
     - [GHSA-wrjc-x8rr-h8h6](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6) (Moderate): Open redirect via backslash in `<Link>` / `useNavigate`.
     - [GHSA-337j-9hxr-rhxg](https://github.com/advisories/GHSA-337j-9hxr-rhxg) (Moderate): SSR hydration constructor injection via `deserializeErrors()`.
   - **Context**: ProcureFlow is a client-side SPA with static preview/bundling and does not use SSR hydration.
   - **Resolution via `--force`**: Bumps `react-router-dom` to `7.x`, which constitutes a major framework upgrade rewriting route configuration and layout conventions.

---

## 3. Policy: Do Not Blindly Run `npm audit fix --force`

- Automated `--force` fixes introduce non-backwards-compatible major upgrades (`vite@8`, `react-router-dom@7`, `recharts@3`).
- Forcing major version bumps risks regressions across component rendering, route resolution, and Vite plugin compilation.
- Upgrades should be evaluated incrementally post-MVP with dedicated regression test passes.

---

## 4. Recharts 3 Migration Note

- **Current Status**: Running `recharts@2.15.4` with `react@18.3.1`.
- **Compatibility**: While Recharts 3 maintains compatibility with React 18, it introduces major breaking API adjustments, revised event handler signatures, and altered responsive container behaviors.
- **Decision**: Recharts 2.x is stable, reliable, and sufficient for ProcureFlow MVP analytics visualizations. Migration to Recharts 3 is deferred to a planned post-MVP refactor.
