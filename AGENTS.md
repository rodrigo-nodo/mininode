# Mininode - Codex repository guide

## Purpose

Mininode is developed through small, reviewable Pull Requests. Use natural-language issues as the task specification and make the smallest change required to satisfy them.

## Default workflow

1. Read this file.
2. Read the GitHub Issue completely.
3. Identify the product/area named by the Issue.
4. Read only the focused context for that area when it exists.
5. Inspect the files directly related to the task first.
6. Expand exploration only when imports, call paths, tests, or failures require it.
7. Implement and run relevant tests.
8. Leave Git operations and PR creation to the automation.

## Repository map

- `frontend/` - static HTML/CSS/JavaScript and Cloudflare-facing frontend code.
- `backend/` - Python/FastAPI backend deployed on Render.
- `.github/workflows/` - GitHub Actions automation. Do not modify unless the Issue explicitly requests it.
- `docs/codex/` - short task context for Codex. Read the relevant file, not every file.

## Focused context routing

- Mininode Privacy / Privacy Web Inspector -> read `docs/codex/privacy.md`.
- Other areas -> rely on the Issue and inspect only the relevant code unless another focused context file is explicitly referenced.

## Rules

- All product changes go through a Pull Request to `main`.
- Never modify `main` directly.
- Prefer small, reversible changes.
- Do not inventory or summarize the entire repository unless the Issue explicitly asks for architecture/repository analysis.
- Do not read unrelated product documentation merely for background.
- Treat the Issue as the source of task-specific facts already investigated by ChatGPT/human review; do not rediscover them unless validation is necessary to implement safely.
- Preserve existing architecture and conventions.
- Run focused tests first; broaden testing when the affected dependency surface requires it.
- Do not weaken security controls unless the Issue explicitly requires a reviewed security change.
- Do not modify `.github/workflows/*`, infrastructure, secrets, deployment configuration, database, authentication, or payments unless explicitly in scope.

## Frontend-only MVP convention

For a new small static MVP, prefer:

```text
frontend/<nombre_mvp>/index.html
```

Start frontend-only when the Issue does not require backend capabilities.

## Pull Request quality

The resulting change should make it easy to answer:

- What changed?
- Why was it needed?
- How was it tested?
- Which files changed?
- Did anything outside the Issue scope change?

Human review is required before merge.