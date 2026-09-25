import json
import threading
import webbrowser
from datetime import datetime

import click
import uvicorn

from hyndsyght import daemon as daemon_module
from hyndsyght import paths
from hyndsyght import status as status_module
from hyndsyght.agentwatch import ingest
from hyndsyght.agentwatch.hook import agent_event_group
from hyndsyght.agentwatch.reaper import recap_reaped_durations
from hyndsyght.api.app import create_app
from hyndsyght.categorize import rules
from hyndsyght.categorize.preview import categorize_group
from hyndsyght.export.days import export_days, to_csv
from hyndsyght.export.tester import rule_test
from hyndsyght.i18n import LOCALES, locale_from_env, t
from hyndsyght.setup.wizard import setup_command
from hyndsyght.store import db
from hyndsyght.store import query as query_store

DEFAULT_PORT = 8420


@click.group()
@click.option(
    "--lang",
    type=click.Choice(LOCALES),
    help="Output language; defaults to LC_ALL, LC_MESSAGES or LANG, then en.",
)
@click.pass_context
def main(ctx: click.Context, lang: str | None) -> None:
    """A lightweight timetracking application with tasteful and easy to usee UI."""
    ctx.obj = lang or locale_from_env()


@main.command()
def init() -> None:
    """Initialize the local event store and categorization rules."""
    db.init_db()
    rules.ensure_default()
    click.echo("hyndsyght initialized.")
    click.echo("Run 'hyndsyght setup' to finish onboarding.")


categorize_group.add_command(rule_test)
main.add_command(categorize_group)
main.add_command(agent_event_group)
main.add_command(setup_command)


@main.command()
def daemon() -> None:
    """Run the unified daemon (baseline watchers + agent-event ingest) forever."""
    daemon_module.run_forever()


@main.command()
@click.option(
    "--once",
    is_flag=True,
    help="Run a single tick and exit, instead of looping forever.",
)
def watch(once: bool) -> None:
    """Foreground watch — refuses to run alongside a live daemon."""
    daemon_module.run_forever(once=once)


@main.command()
@click.option("--json", "as_json", is_flag=True, help="Emit the raw JSON report.")
def status(as_json: bool) -> None:
    """Show daemon/hook/DB health."""
    report = status_module.report()
    click.echo(json.dumps(report) if as_json else status_module.render_human(report))


@main.command()
@click.option(
    "--port",
    default=DEFAULT_PORT,
    show_default=True,
    help="Port to serve the dashboard on.",
)
@click.option("--no-open", is_flag=True, help="Don't open the dashboard in a browser.")
def serve(port: int, no_open: bool) -> None:
    """Serve the dashboard + REST API on 127.0.0.1."""
    if not no_open:
        # ponytail: fixed 0.6s delay assumes near-instant bind — swap for a
        # port-poll loop if this ever races.
        threading.Timer(
            0.6, webbrowser.open, args=(f"http://127.0.0.1:{port}",)
        ).start()
    uvicorn.run(create_app(port), host="127.0.0.1", port=port)


@main.command()
@click.option(
    "--port",
    default=DEFAULT_PORT,
    show_default=True,
    help="Port to serve the dashboard on.",
)
@click.pass_obj
def tray(locale: str, port: int) -> None:
    """Menu-bar app: hosts the dashboard and shows today's time and quick controls."""
    from hyndsyght.tray.app import run  # lazy: AppKit only loads for this command

    run(locale, port)


@main.command("query")
@click.option(
    "--sql",
    "sql_text",
    required=True,
    help="SQL to run against the read-only event store.",
)
@click.option("--json", "as_json", is_flag=True, help="Emit results as JSON.")
def query_cmd(sql_text: str, as_json: bool) -> None:
    """Run a read-only SQL query against the event store."""
    rows = query_store.run_sql(sql_text)
    if as_json:
        click.echo(json.dumps(rows))
        return
    for row in rows:
        click.echo(row)


_DAY = click.DateTime(["%Y-%m-%d"])
# Help text is built at import, before --lang is parsed, so it follows the env.
_HELP_LOCALE = locale_from_env()


@main.command("export", help=t("export.help", _HELP_LOCALE))
@click.option("--since", type=_DAY, required=True, help=t("export.since", _HELP_LOCALE))
@click.option("--until", type=_DAY, help=t("export.until", _HELP_LOCALE))
@click.option(
    "--json",
    "fmt",
    flag_value="json",
    default=True,
    help=t("export.json", _HELP_LOCALE),
)
@click.option("--csv", "fmt", flag_value="csv", help=t("export.csv", _HELP_LOCALE))
def export_cmd(since: datetime, until: datetime | None, fmt: str) -> None:
    last = (until or datetime.now().astimezone()).date()
    result = export_days(since.date(), last, rules.load_rules())
    click.echo(json.dumps(result) + "\n" if fmt == "json" else to_csv(result), nl=False)


@main.command("repair")
@click.pass_obj
def repair(locale: str) -> None:
    """Fix agent event rows left broken by earlier ingest bugs."""
    conn = db.connect(paths.db_path())
    restored = ingest.backfill_agent_cwd(conn)
    capped = recap_reaped_durations(conn)
    removed = ingest.delete_unmatched_closes(conn)
    click.echo(t("cli.repair.cwd_restored", locale, count=restored))
    click.echo(t("cli.repair.durations_capped", locale, count=capped))
    click.echo(t("cli.repair.phantoms_removed", locale, count=removed))


@main.group("mcp")
def mcp_group() -> None:
    """MCP server commands (requires the `mcp` extra: uv sync --extra mcp)."""


@mcp_group.command("serve")
def mcp_serve() -> None:
    """Run the read-only MCP server over stdio."""
    from hyndsyght.mcpserver.server import mcp  # lazy: fastmcp is an optional extra

    mcp.run()


if __name__ == "__main__":
    main()
