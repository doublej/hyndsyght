"""`hyndsyght setup` — idempotent onboarding: init, global install, hooks,
Screen Recording permission check, daemon, menu-bar app. Safe to rerun.
"""

import subprocess
from pathlib import Path

import click

from hyndsyght import status as status_module
from hyndsyght.categorize import rules
from hyndsyght.platform import window_watcher
from hyndsyght.setup import daemon as daemon_setup
from hyndsyght.setup import hooks as hooks_setup
from hyndsyght.status import CLAUDE_SETTINGS_PATH, SCREEN_RECORDING_PANE_URL
from hyndsyght.store import db

# uv's default `uv tool install` bin dir. Checking this directly (rather than
# shutil.which) matters because `just setup` runs this via `uv run`, which
# always prepends the repo's own .venv/bin to PATH — shutil.which("hyndsyght")
# would find that local venv binary and wrongly report "already installed".
UV_TOOL_BIN = Path.home() / ".local" / "bin" / "hyndsyght"


@click.command("setup")
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation prompts.")
def setup_command(yes: bool) -> None:
    """Idempotent onboarding wizard: init, install, hooks, permission, daemon."""
    repo_root = Path.cwd()
    db.init_db()
    rules.ensure_default()
    click.echo("Database + rules ready.")

    _step_install(repo_root)
    _step_hooks(yes)
    _step_permission()
    _step_daemon(repo_root, yes)
    _step_tray(repo_root, yes)

    click.echo("\nOpen the dashboard from the menu-bar icon, or run 'hyndsyght serve'.")


def _step_install(repo_root: Path) -> None:
    if UV_TOOL_BIN.exists():
        return
    click.echo("Installing hyndsyght globally (uv tool install .)...")
    subprocess.run(["uv", "tool", "install", "."], cwd=repo_root, check=False)


def _step_hooks(yes: bool) -> None:
    if not yes and not click.confirm(
        "Install Claude Code hooks for agent-activity tracking?", default=True
    ):
        return
    added = hooks_setup.install(CLAUDE_SETTINGS_PATH)
    count = sum(added.values())
    click.echo(f"Hooks: {count} added, {len(added) - count} already present.")
    if count:
        click.echo(
            "Restart Claude Code (or start a new session) — "
            "it only reads hooks at session start."
        )


def _step_permission() -> None:
    window_watcher().poll()  # forces macOS to list this terminal under Screen Recording
    if status_module.report()["window_titles_empty_last_hour"]:
        click.echo("Screen Recording permission looks missing.")
        click.echo(f'  → open "{SCREEN_RECORDING_PANE_URL}"')
    else:
        click.echo("Screen Recording permission looks OK.")


def _step_daemon(repo_root: Path, yes: bool) -> None:
    if not yes and not click.confirm(
        "Install and start the background daemon via launchd?", default=True
    ):
        return
    if not daemon_setup.service_install(repo_root):
        click.echo("Daemon install failed — see output above.")
        return
    click.echo("Daemon installed and started.")
    click.echo(daemon_setup.register_in_atlas(repo_root))


def _step_tray(repo_root: Path, yes: bool) -> None:
    if not yes and not click.confirm("Start the menu-bar app at login?", default=True):
        return
    if not daemon_setup.service_install(repo_root, "tray"):
        click.echo("Menu-bar app install failed — see output above.")
        return
    click.echo("Menu-bar app installed and started.")
    click.echo(daemon_setup.register_in_atlas(repo_root, "tray"))
