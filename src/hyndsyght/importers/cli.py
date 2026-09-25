"""`hyndsyght import activitywatch` — bring ActivityWatch history into the store."""

import math
import sqlite3
import urllib.error
from datetime import datetime
from pathlib import Path

import click

from hyndsyght import paths
from hyndsyght.categorize import rules as rules_module
from hyndsyght.i18n import locale_from_env, t
from hyndsyght.importers import activitywatch as aw
from hyndsyght.store import db

_HELP_LOCALE = locale_from_env()


@click.group("import", help=t("importer.help", _HELP_LOCALE))
def import_group() -> None:
    pass


@import_group.command("activitywatch", help=t("importer.aw.help", _HELP_LOCALE))
@click.option(
    "--url",
    default=aw.DEFAULT_URL,
    show_default=True,
    help=t("importer.aw.url", _HELP_LOCALE),
)
@click.option(
    "--file",
    "export_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help=t("importer.aw.file", _HELP_LOCALE),
)
@click.option(
    "--host", "hosts", multiple=True, help=t("importer.aw.host", _HELP_LOCALE)
)
@click.option("--dry-run", is_flag=True, help=t("importer.aw.dry_run", _HELP_LOCALE))
@click.option("--undo", is_flag=True, help=t("importer.aw.undo", _HELP_LOCALE))
@click.pass_obj
def activitywatch(
    locale: str,
    url: str,
    export_file: Path | None,
    hosts: tuple[str, ...],
    dry_run: bool,
    undo: bool,
) -> None:
    db.init_db()
    rules_module.ensure_default()
    conn = db.connect(paths.db_path())
    if undo:
        click.echo(t("importer.aw.removed", locale, count=aw.remove_imported(conn)))
        return
    source = aw.FileSource(export_file) if export_file else aw.ApiSource(url)
    buckets = aw.select_buckets(_buckets(source, url, locale), hosts)
    if not buckets:
        raise click.ClickException(t("importer.aw.none", locale))
    until = aw.native_start(conn)
    _import_all(conn, source, buckets, until, write=not dry_run, locale=locale)


def _buckets(source: aw.Source, url: str, locale: str) -> dict[str, aw.Bucket]:
    try:
        return source.buckets()
    except urllib.error.URLError as error:
        raise click.ClickException(
            t("importer.aw.unreachable", locale, url=url)
        ) from error


def _import_all(
    conn: sqlite3.Connection,
    source: aw.Source,
    buckets: dict[str, aw.Bucket],
    until: float,
    *,
    write: bool,
    locale: str,
) -> None:
    rules = rules_module.load_rules()
    total = 0
    for bucket_id, bucket in buckets.items():
        result = aw.import_bucket(
            conn, source, bucket_id, bucket, rules, until, write=write
        )
        click.echo(_bucket_line(result, locale))
        total += result.rows
    if not math.isinf(until):
        click.echo(
            t("importer.aw.cutoff", locale, time=_local(until, "%Y-%m-%d %H:%M"))
        )
    click.echo(
        t(
            "importer.aw.done" if write else "importer.aw.dry_run_done",
            locale,
            rows=total,
        )
    )


def _bucket_line(result: aw.BucketResult, locale: str) -> str:
    if result.first is None or result.last is None:
        return t("importer.aw.bucket_empty", locale, bucket=result.bucket_id)
    line = t(
        "importer.aw.bucket",
        locale,
        bucket=result.bucket_id,
        rows=result.rows,
        first=_local(result.first, "%Y-%m-%d"),
        last=_local(result.last, "%Y-%m-%d"),
    )
    if result.hidden:
        line += " " + t("importer.aw.hidden", locale, count=result.hidden)
    return line


def _local(ts: float, fmt: str) -> str:
    return datetime.fromtimestamp(ts).astimezone().strftime(fmt)
