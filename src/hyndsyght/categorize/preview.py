"""`hyndsyght categorize preview` — dry-run a title against the rules, or list them."""

import click

from hyndsyght.categorize.exclude import is_away, should_redact
from hyndsyght.categorize.match import categorize
from hyndsyght.categorize.rules import load_rules


@click.group("categorize")
def categorize_group() -> None:
    """Categorization rule tools."""


@categorize_group.command("preview")
@click.argument("title", required=False)
def preview(title: str | None) -> None:
    """Classify TITLE against the current rules, or list all rules if omitted."""
    rules = load_rules()
    if title is None:
        for name, patterns in rules.categories:
            click.echo(f"{name}: {[p.pattern for p in patterns]}")
        click.echo(f"redact: {[p.pattern for p in rules.redact_patterns]}")
        click.echo(f"away: {[p.pattern for p in rules.away_patterns]}")
        return
    if is_away(title, rules):
        click.echo("away")
        return
    if should_redact(title, rules):
        click.echo("redacted")
        return
    click.echo(categorize(title, "window", rules))
