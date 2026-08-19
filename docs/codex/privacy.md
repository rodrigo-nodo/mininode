# Codex context - Mininode Privacy

Use this file only for issues whose scope is Mininode Privacy or the Privacy Web Inspector.

## Product scope

Mininode Privacy performs an initial diagnostic of public privacy signals on a website. It is not a legal certification or a complete compliance audit.

## Technical focus

- Backend: Python / FastAPI on Render.
- Frontend: static HTML/CSS/JavaScript on Cloudflare Pages.
- Current Web Inspector work belongs in the existing Privacy/backend implementation and its tests.
- Preserve the current public API contract unless the issue explicitly requests a contract change.

## Security invariants

- SSRF protections are mandatory.
- Never allow private, loopback, link-local, reserved, mixed public/private, or otherwise disallowed destinations merely to increase coverage.
- Validate redirects before following them.
- Prefer a safe fallback or a precise failure over weakening SSRF controls.
- Keep diagnostic/technical telemetry private; do not expose internal network details in the public Privacy response.

## Implementation rules

- Start from the files named or implied by the issue; do not inventory the whole repository by default.
- Search outward only when an import, call path, test, or failing behavior requires it.
- Reuse existing Web Inspector/fetcher abstractions rather than introducing a parallel fetch stack.
- Keep changes minimal and reversible.
- Add or update focused regression tests for each behavior changed.
- Do not modify `.github/workflows/*` unless the issue explicitly requires workflow changes.
- Do not modify unrelated frontend, database, authentication, payments, or infrastructure.

## Current Web Inspector investigation baseline

The validated education sample established these distinct cases:

- `insucap.cl`: redirect validation reaches `insucapchile.cl` and is blocked by SSRF. Investigate why; do not relax SSRF globally.
- `cyfcapacitacion.cl`: reaches the server after redirect to `www` and receives HTTP 500. Treat as an origin-site/server failure unless new evidence shows otherwise.
- `colegioelalbademacul.com`: responds HTTP 403 quickly. Candidate for conservative browser-compatible request headers/fallback while preserving security.
- `colegiosochides.cl`: connection attempt ends in `ConnectTimeout` around the configured timeout. Diagnose/fallback conservatively; do not simply hide the timeout by making it unbounded.

Known-good regression sites from the same cleaned sample include:

- `delucchicapacita.cl`
- `academiaelcentro.cl`
- `colegio-forjadores.cl`
- `charlesdarwin.cl`

When changing fetch behavior, preserve successful behavior for the known-good cases through focused automated tests where feasible; external live-site tests should not become required unit tests.

## Definition of done for Privacy fetcher issues

1. Smallest safe implementation for the issue.
2. SSRF invariants preserved.
3. Focused tests pass.
4. Existing relevant tests pass.
5. No unrelated files changed.
6. Final message states files changed, tests run, and any unresolved case.