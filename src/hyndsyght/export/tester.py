"""`hyndsyght categorize test`: what each rule matched over recent history, in hours.

Rows are classified exactly as the export does: AFK-clipped window rows with their
app (payload extra) and agent project, plus agent rows matched on their `cwd`.
"""

from datetime import date, datetime, timedelta
from typing import Any, NamedTuple

import click

from hyndsyght.categorize.match import UNCATEGORIZED, categorize, client_of
from hyndsyght.categorize.rules import Rules, load_rules
from hyndsyght.export.days import classified_rows
from hyndsyght.export.project import agent_turns
from hyndsyght.i18n import locale_from_env, t
from hyndsyght.insights.activity import load_spans
from hyndsyght.insights.intervals import day_bounds

TOP = 5
_HELP_LOCALE = locale_from_env()


class Entry(NamedTuple):
    category: str
    client: str | None
    label: str  # the title (or app), or an agent's cwd
    seconds: float


def entries_between(first: date, last: date, rules: Rules) -> list[Entry]:
    start, end = day_bounds(str(first))[0], day_bounds(str(last))[1]
    spans, turns = load_spans(start, end), agent_turns(start, end)
    days = [str(first + timedelta(n)) for n in range((last - first).days + 1)]
    windows = [
        _window_entry(item)
        for day in days
        for item in classified_rows(spans, turns, rules, day)
    ]
    return windows + [_agent_entry(turn, rules, start, end) for turn in turns]


def _window_entry(item: dict[str, Any]) -> Entry:
    label = item["title"] or item["app"] or "?"
    if item["project"]:
        label = f"{label} [{item['project']}]"
    seconds = item["interval"][1] - item["interval"][0]
    return Entry(item["category"] or UNCATEGORIZED, item["client"], label, seconds)


def _agent_entry(turn: dict[str, Any], rules: Rules, start: float, end: float) -> Entry:
    seconds = min(end, turn["ts_end"]) - max(start, turn["ts_start"])
    category = categorize(None, "claude-code-turn", rules, turn["cwd"])
    return Entry(category, client_of(None, rules, turn["cwd"]), turn["cwd"], seconds)


def summarize(
    entries: list[Entry], field: str
) -> list[tuple[str, float, list[tuple[str, float]]]]:
    """Per category or client: total seconds and the labels with the most time."""
    groups: dict[str, dict[str, float]] = {}
    for entry in entries:
        if name := getattr(entry, field):
            labels = groups.setdefault(name, {})
            labels[entry.label] = labels.get(entry.label, 0.0) + entry.seconds
    summary = [
        (name, sum(labels.values()), _top(labels)) for name, labels in groups.items()
    ]
    return sorted(summary, key=lambda group: group[1], reverse=True)


def _top(labels: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(labels.items(), key=lambda item: item[1], reverse=True)[:TOP]


@click.command("test", help=t("tester.help", _HELP_LOCALE))
@click.option(
    "--days", default=7, show_default=True, help=t("tester.days", _HELP_LOCALE)
)
@click.pass_obj
def rule_test(locale: str, days: int) -> None:
    last = datetime.now().astimezone().date()
    entries = entries_between(last - timedelta(days - 1), last, load_rules())
    if not entries:
        click.echo(t("tester.empty", locale, days=days))
        return
    for field in ("category", "client"):
        click.echo(t(f"tester.{field}", locale))
        for name, seconds, labels in summarize(entries, field):
            click.echo(f"  {name}  {seconds / 3600:.1f}h")
            for label, label_seconds in labels:
                click.echo(f"    {label_seconds / 3600:6.1f}h  {label}")
