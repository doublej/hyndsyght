import json
from pathlib import Path

from click.testing import CliRunner

from hyndsyght.agentwatch.hook import agent_event_group


def test_record_appends_stdin_json_to_spool_without_touching_db(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr("hyndsyght.paths.state_dir", lambda: tmp_path)
    payload = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "s1",
        "prompt_id": "p1",
    }

    result = CliRunner().invoke(
        agent_event_group, ["record"], input=json.dumps(payload)
    )

    assert result.exit_code == 0
    assert not (tmp_path / "hyndsyght.db").exists()
    spooled = json.loads((tmp_path / "agent-events.jsonl").read_text().strip())
    assert spooled["session_id"] == "s1"
    assert "_received_at" in spooled
