# Repository Guidelines

## Project Structure & Module Organization

- `src/gapless_crypto_data/` contains production code; keep new runtime logic under existing subpackages (`collectors`, `gap_filling`, `utils`, `validation`) and surface entry points via `api.py`.
- `tests/` mirrors the package with pytest suites and shared fixtures in `tests/fixtures/`; add datasets to `sample_data/` only if they support multiple cases.
- `docs/` and `examples/` store contributor guidance; generated artifacts land in `dist/` and should be recreated via tooling, not edited.

## Documentation & Planning Resources

- For quick context, read `docs/SSOT_PLANNING_SUMMARY.md`; consult `docs/SSOT_DOCUMENTATION_ARCHITECTURE.yaml` for the full specification and `docs/DOCUMENTATION_INVENTORY.yaml` to track coverage gaps.
- When adding or revising docs, update the inventory alongside the primary markdown or YAML source.

## Build, Test, and Development Commands

- `uv sync --dev` – provision the locked toolchain.
- `uv run pytest` – run the suite; scope with `::` selectors for targeted debugging.
- `uv run ruff format --check .` / `uv run ruff check .` – formatting and linting; pass `--fix` locally before committing.
- `uv run mypy src/` – enforce typing, especially on public API boundaries.
- `uv build` – create wheel and sdist for release smoke tests.

## Coding Style & Naming Conventions

- Standard Python: 4-space indentation, type hints, Google-style docstrings on public members.
- Use `snake_case` for modules and functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants; keep imports deterministic and prefer explicit exports inside `__all__`.
- Ruff is the source of truth; avoid mixing Black/isort configs.

## Testing Guidelines

- Pytest is configured with `-ra -q --strict-markers`; declare any new marker in `tests/conftest.py`.
- Extend fixtures instead of hard-coding data, and exercise both gap-filling flows and collector paths when adding features.
- For release work, run `uv run pytest --cov=src/gapless_crypto_data` to watch coverage.

## Commit & Pull Request Guidelines

- Use Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) aligned with the Git history.
- Prior to push, ensure `uv run pytest`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy src/`, and `uv run pre-commit run --all-files` succeed.
- PRs should describe behavior changes, reference issues, and update `CHANGELOG.md`, `README.md`, or docs when user-facing behavior shifts.

## Security & Configuration Tips

- Store sensitive configuration in environment variables; never commit API keys or Binance credentials.
- Reuse the atomic file helpers in `utils/` for resume metadata and CSV writes to avoid partial writes.
