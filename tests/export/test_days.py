from datetime import date

from click.testing import CliRunner

from hyndsyght.categorize.rules import Rules
from hyndsyght.cli import main
from hyndsyght.export.days import export_days, to_csv

DAY, NEXT_DAY = "2026-09-24", "2026-09-25"  # the fixture day in conftest.py


def _export(rules: Rules) -> dict:
    return export_days(date.fromisoformat(DAY), date.fromisoformat(NEXT_DAY), rules)


def test_export_rows_follow_the_schema_1_contract(rules: Rules) -> None:
    day, next_day = _export(rules)["days"]
    assert (day["date"], day["human_seconds"]) == (DAY, 20700)
    assert day["unclassified_seconds"] == 900
    assert [(r["id"], r["seconds"]) for r in day["rows"]] == [
        (f"hyndsyght:{DAY}:-:acme.globex:dev.browser", 9000),
        (f"hyndsyght:{DAY}:python/finances:initech:dev", 3600),
        (f"hyndsyght:{DAY}:-:-:business.ops.admin", 1800),
        (f"hyndsyght:{DAY}:-:-:communication", 1800),
    ]
    assert next_day["rows"][0]["seconds"] == 1800  # the rest of the midnight row


def test_export_evidence_names_apps_titles_and_agent_time(rules: Rules) -> None:
    rows = {r["category"]: r for r in _export(rules)["days"][0]["rows"]}
    assert rows["dev"]["project"] == "python/finances"
    assert rows["dev"]["evidence"] == {
        "apps": [["iTerm2", 3600]],
        "titles": [["✳ umber-weasel", 3600]],
        "agent_seconds": 1800,
    }
    assert rows["business.ops.admin"]["evidence"]["titles"] == []
    assert rows["dev.browser"]["evidence"]["agent_seconds"] == 0


def test_export_leaves_private_time_out_of_the_rows(rules: Rules) -> None:
    day = _export(rules)["days"][0]
    assert all(r["category"] != "private.admin.property" for r in day["rows"])
    classified = sum(r["seconds"] for r in day["rows"]) + day["unclassified_seconds"]
    assert day["human_seconds"] - classified == 3600  # the private hour


def test_csv_gives_client_hours_per_day_in_quarters(rules: Rules) -> None:
    assert to_csv(_export(rules)) == (
        f"date,client,hours\n{DAY},acme.globex,2.5\n{DAY},initech,1.0\n"
    )


def test_export_command_prints_json_and_csv(rules: Rules) -> None:
    args = ["export", "--since", DAY, "--until", DAY]
    as_json = CliRunner().invoke(main, args)
    assert as_json.exit_code == 0 and '"schema": 1' in as_json.output
    as_csv = CliRunner().invoke(main, [*args, "--csv"])
    assert as_csv.output.startswith("date,client,hours\n")
