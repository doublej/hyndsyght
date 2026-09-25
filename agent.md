# hyndsyght

> A lightweight timetracking application with tasteful and easy to usee UI.

## Stack

- Python 3.13, uv, ruff, mypy, pytest
- CLI framework: Click

## Commands

Use `just` as the task runner:

- `just check` — run all checks (just-fmt-check + loc-check + dir-check + lint + format-check + typecheck + test)
- `just install` — sync dependencies (`uv sync`)
- `just run` — run the CLI
- `just lint` / `just lint-fix` — ruff check / --fix
- `just format` / `just format-check` — ruff format / --check
- `just typecheck` — mypy
- `just test` — pytest
- `just loc-check` — check file lengths (thresholds in `.quality.json`)
- `just dir-check` — check files per directory (thresholds in `.quality.json`)
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Project Structure

```
src/hyndsyght/
├── agentwatch/      # Claude Code hook spool + ingest + reap
├── api/             # FastAPI app: auth, routes, dashboard host
├── categorize/      # title → category rules (TOML, hand-edited)
├── insights/        # Attention Physics + Leverage Ledger computations
├── mcpserver/       # read-only MCP server over the event store
├── platform/        # macOS watchers (window/AFK/media) behind a Protocol seam
├── setup/           # `hyndsyght setup` — hooks, daemon, wizard
├── store/           # SQLite schema, connection, queries
├── cli.py           # Click CLI entry point
├── daemon.py        # the one background process
├── paths.py         # state-dir file locations
└── status.py        # health report + human-readable rendering
web/                 # SvelteKit dashboard
launchd/             # launchd plist template (generated + .example)
pyproject.toml       # project config, dependencies, script entry point
Justfile             # task runner
```

## Conventions

- src/ layout with hatchling build backend
- Module name: `hyndsyght`
- Entry point: `hyndsyght.cli:main`
- Keep functions small (5–10 lines target, 20 max)
- Prefer explicit, readable code over cleverness
- Handle errors at boundaries; let unexpected errors surface
- User-facing text goes through `t()` with keys in `locales/en.json` (base, fallback) and `locales/nl.json` (informal je/jij); logs and developer errors stay English

## Agent

### Verify Loop

Run after every change: `just check`

Runs: just-fmt-check + loc-check + dir-check + i18n-check + lint + format-check + typecheck + test.

Step-by-step alternative:

1. `just lint-fix`
2. `just format`
3. `just typecheck`
4. `just test`

### Auto-fixable

- `uv run ruff check --fix src/ tests/` — auto-fix lint issues
- `uv run ruff format src/ tests/` — format code

### Common Tasks

- Add a Click command: define a function decorated with `@cli.command()` in `cli.py`
- Add a command group: use `@click.group()` and register subcommands
- Add a subcommand module: create a new file in the package, import and register in `cli.py`
- Add an onboarding step: new function in `setup/wizard.py`, called from `setup_command`
- Add a dependency: `uv add <package>`
- Add or change user-facing text: edit every `src/hyndsyght/locales/*.json`, call `t("hello.greeting", locale, name=...)`, run `just i18n-check`

### Testing

- Test files: `tests/test_*.py`
- Use `click.testing.CliRunner` for CLI tests
- Run a single test: `uv run pytest tests/test_foo.py::test_name -v`

### Boundaries

- Do not deploy, publish, or push
- Do not modify `[tool.*]` sections in `pyproject.toml` without asking
