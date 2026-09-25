# hyndsyght

> A lightweight timetracking application with tasteful and easy to usee UI.

## What this is

A Python command-line tool built on Click. Single binary entry point declared in `pyproject.toml`, dependencies managed by `uv`, quality enforced by `ruff` / `mypy` / `pytest` and the `.quality.json` thresholds.

## Mental model

```
src/hyndsyght/
├── __init__.py
├── cli.py          # Click entry point — function `main`
├── i18n.py         # `t()` + locale resolution: --lang → LC_ALL / LC_MESSAGES / LANG → en
├── tray/           # `hyndsyght tray`: menu-bar app hosting the dashboard; model.py is AppKit-free
└── locales/        # en.json (base, fallback) + nl.json — every user-facing string
pyproject.toml      # [project.scripts] binds `hyndsyght` → `hyndsyght.cli:main`
```

The runtime path is `console_script → cli.main → Click command tree`. New commands are decorators attached to a `click.Group`. The package is intentionally flat: add modules under `hyndsyght/` only when `cli.py` outgrows itself.

## Invariants

- `src/` layout with hatchling — do not move code to a top-level package.
- Module name is `hyndsyght` (slug with `-` → `_`); script entry point is `hyndsyght.cli:main`.
- Functions stay small (5–10 lines target, 20 max — enforced by code review, not lint).
- Errors surface at the boundary; do not wrap unexpected exceptions in `try/except`.
- `uv` owns the lockfile. Add deps with `uv add <pkg>`, never edit `[project.dependencies]` by hand.
- The daemon runs no event loop, so AppKit state never refreshes in it. Read frontmost-window
  state from Quartz's window list; `NSWorkspace.frontmostApplication()` silently returns the app
  that was frontmost at process start, forever.
- Closing an agent event must MERGE its payload, never replace it. The open carries the
  session and the project (`cwd`); the close carries the intent. A replacing write silently
  destroys the project on ~89% of agent rows, and only the spool can get it back.
- The dashboard skips fetching while `document.hidden`. Browser automation reports a tab as hidden
  even when the window is focused, so the app looks blank and dead. Force
  `Object.defineProperty(document,'hidden',{get:()=>false})` in the page before judging any screen.
- Pause is a file, `paused-until` in the state dir (epoch seconds, `inf` = until resumed). The
  daemon reads it each tick and skips window and media capture while it holds a future time;
  AFK and agent ingest keep running. The tray writes it; nothing else needs to know.
- User-facing text is multilingual: `en` (base, fallback) and `nl` (informal je/jij). Never hardcode user-visible strings; add each key to every language file in the same change. Logs and developer errors stay English.

## Common change patterns

- **Add a command** → new `@cli.command()` (or `@<group>.command()`) function in `cli.py`.
- **Add a flag** → `@click.option()` decorator above the command function.
- **Extract a subcommand group** → `click.Group()` in a new module, registered via `cli.add_command(...)`.
- **Add a dependency** → `uv add <pkg>` (or `uv add --dev <pkg>`).
- **Add or change text** → edit `src/hyndsyght/locales/*.json`, call `t("hello.greeting", locale, name=...)` with the locale from `@click.pass_obj`, run `just i18n-check`.
- **Add a language** → add `src/hyndsyght/locales/<locale>.json` (no registration: `LOCALES` discovers it and `--lang` offers it), run `just i18n-check`.

## Verification

Run `just check` after every change. It composes:

`just-fmt-check` + `loc-check` + `dir-check` + `i18n-check` + `lint` + `format-check` + `typecheck` + `test`

Recipe reference:

- `just install` — `uv sync`
- `just run-cli` — run the CLI (alias `just run`)
- `just lint` / `just lint-fix` — ruff check / `--fix`
- `just format` / `just format-check` — ruff format / `--check`
- `just typecheck` — mypy
- `just test` — pytest
- `just loc-check` / `just dir-check` — file-size and per-directory thresholds from `.quality.json`
- `just i18n-check` — every language file has the base's keys and placeholders
- `just just-fmt-check` — verify Justfile formatting
- `just clean` — remove build artifacts and caches
- `just update-scaffold` — pull updates from the cookiecutter template

## Related context

- [agent.md](agent.md) — verify loop, auto-fix commands, common tasks, boundaries
- `.claude/` — Claude Code settings, scaffold-update hook, library-freshness hook, diagnostic logging
- `.quality.json` — loc / dir thresholds (single source of truth)
- As this project grows past a single `cli.py`, add nested `CLAUDE.md` files in high-value subfolders (domain logic, integrations) following the `claude-md-tree` skill's context-packet pattern.

<!-- agent-log:policy -->
### Shared agent journal

Use `./agent-log` (a shim for `atlas agent-log` — both are identical) for short-lived
operational awareness between concurrent agents. It is not chat and not a task tracker: the
issue tracker remains the source of truth for ownership, blockers, and durable findings.

- Run `./agent-log recent` before interpreting shared state.
- Before an action that can change another agent's observations, write an intent with every
  affected scope. This includes shared-worktree edits, generated artifacts, git/index
  mutations, and shared ports, processes, or services.
- Run builds, tests, and deployments through the wrapper so start, commit, dirty state,
  duration, exit code, and outcome are recorded even on failure:
  `./agent-log run build|test|deploy --scope <resource> [--bead <id>] -- <command...>`.
- For manual operations, use `./agent-log begin <operation> --scope <resource> [--bead <id>]
  -- <summary>` and always close the returned id with `./agent-log end <id> --outcome
  ok|failed|cancelled -- <result>`. `<operation>` is one of build, commit, deploy, edit, implement, investigate, merge, push, review, sync, test — what
  makes this particular run specific goes in the summary, never in an invented operation name.
- Record a temporary result-affecting discovery with `./agent-log finding --scope <resource>
  --evidence <fact> [--bead <id>] -- <summary>`. This is the entry that saves another agent a
  wasted run, and the one most often skipped — write one whenever you learn something that
  would change what a concurrent agent does next, especially a dead end. Promote lasting
  knowledge to the issue tracker or the relevant doc.
- At session end, write `./agent-log handoff -- <stopping point + next step>` — the durable
  baton the next session's briefing picks up. Handoffs never expire; the latest one is
  always shown by `recent`.
- Intents expire after 20 minutes and findings after 4 hours unless `--ttl` overrides them.
  Renew by closing and reopening an intent; never treat an expired entry as current.
- Keep summaries factual and short. Do not reply, ask questions, mention agents, narrate
  routine progress, or log isolated reads/edits/tests that cannot affect anyone else.

Canonical scopes are `path:<repo-relative-path>`, `artifact:<name>`, `service:<name>`,
`host:<name>`, `port:<number>`, and `git:<worktree-or-ref>`; a repo may define additional
canonical scopes of its own. Add multiple `--scope` flags when needed. The journal SQLite db
lives in the git common directory, so linked worktrees share it without dirtying the repo.


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:1105d646 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/core-concepts/sync-concepts.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
