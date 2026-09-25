import json
from pathlib import Path

from hyndsyght.setup import daemon


def test_ensure_plist_substitutes_repo_root_and_home(tmp_path: Path) -> None:
    repo_root = tmp_path / "hyndsyght"
    repo_root.mkdir()
    home = tmp_path / "home"

    plist_path = daemon.ensure_plist(repo_root, home=home)

    content = plist_path.read_text()
    assert str(repo_root) in content
    assert str(home) in content
    assert "com.hyndsyght.daemon" in content
    assert plist_path == repo_root / "launchd" / "com.hyndsyght.daemon.plist"


def test_register_in_atlas_returns_clean_message_when_absent(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        daemon, "ATLAS_DAEMONS_PATH", tmp_path / "missing" / "daemons.json"
    )

    result = daemon.register_in_atlas(tmp_path / "repo")

    assert "not found" in result


def test_register_in_atlas_adds_when_absent(tmp_path: Path, monkeypatch) -> None:
    atlas_path = tmp_path / "daemons.json"
    atlas_path.write_text(json.dumps({"version": 1, "daemons": []}))
    monkeypatch.setattr(daemon, "ATLAS_DAEMONS_PATH", atlas_path)

    result = daemon.register_in_atlas(tmp_path / "repo")

    assert result == "registered in project-atlas"
    data = json.loads(atlas_path.read_text())
    assert any(d["label"] == "com.hyndsyght.daemon" for d in data["daemons"])


def test_register_in_atlas_no_ops_when_already_present(
    tmp_path: Path, monkeypatch
) -> None:
    atlas_path = tmp_path / "daemons.json"
    atlas_path.write_text(
        json.dumps({"version": 1, "daemons": [{"label": "com.hyndsyght.daemon"}]})
    )
    monkeypatch.setattr(daemon, "ATLAS_DAEMONS_PATH", atlas_path)

    result = daemon.register_in_atlas(tmp_path / "repo")

    assert result == "already registered in project-atlas"
    data = json.loads(atlas_path.read_text())
    assert len(data["daemons"]) == 1


def test_tray_plist_restarts_only_after_a_crash(tmp_path: Path) -> None:
    content = daemon.ensure_plist(tmp_path, home=tmp_path, command="tray").read_text()
    assert "<string>com.hyndsyght.tray</string>" in content
    assert "<string>tray</string>" in content
    assert "<key>SuccessfulExit</key>" in content
    assert "<string>Aqua</string>" in content
    assert "tray.err.log" in content


def test_daemon_plist_keeps_always_restarting(tmp_path: Path) -> None:
    content = daemon.ensure_plist(tmp_path, home=tmp_path).read_text()
    assert "<key>KeepAlive</key>\n\t<true/>" in content
    assert "SuccessfulExit" not in content
    assert "LimitLoadToSessionType" not in content
    assert "<string>daemon</string>" in content


def test_register_in_atlas_adds_the_tray(tmp_path: Path, monkeypatch) -> None:
    atlas_path = tmp_path / "daemons.json"
    atlas_path.write_text(
        json.dumps({"version": 1, "daemons": [{"label": "com.hyndsyght.daemon"}]})
    )
    monkeypatch.setattr(daemon, "ATLAS_DAEMONS_PATH", atlas_path)

    assert daemon.register_in_atlas(tmp_path, "tray") == "registered in project-atlas"
    entry = json.loads(atlas_path.read_text())["daemons"][1]
    assert entry["label"] == "com.hyndsyght.tray"
    assert entry["logs"]["stderr"] == "~/Library/Logs/hyndsyght/tray.err.log"
