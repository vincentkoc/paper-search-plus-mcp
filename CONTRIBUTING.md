# Contributing

## Workflow

1. Create a task branch from an up-to-date remote base using `gwt new vincentkoc-code/<topic>`.
2. Keep changes focused. Prefer one draft PR per source integration, bug fix, or documentation task.
3. Run the local checks before pushing:

```bash
uv sync --group dev
uv run pytest -q
uv run paper-search-plus-mcp --list-tools
uv build --wheel
```

## Source Intake Rules

- Prefer official APIs and open repositories.
- Do not expose scraping-heavy or legally risky sources on the default public surface.
- If you import upstream work, preserve attribution with cherry-picks where possible and isolate follow-up fixes in separate commits.

## Tests

- Add mocked unit tests for parser and transport logic.
- Keep live provider checks under `tests/live/` and guard them with `PAPER_SEARCH_PLUS_LIVE_SMOKE=1`.
- Update the golden contract fixtures when the public tool surface or source capability contract changes intentionally.

## Pull Requests

- Use the provided PR template.
- Link related issues with `Fixes #<issue>`.
- Include behavior changes, test coverage, and any source-policy implications in the description.
