from pathlib import Path

from hyndsyght.setup import wizard


def test_step_install_skips_when_already_globally_installed(
    tmp_path: Path, monkeypatch
) -> None:
    bin_path = tmp_path / "hyndsyght"
    bin_path.touch()
    monkeypatch.setattr(wizard, "UV_TOOL_BIN", bin_path)
    calls = []
    monkeypatch.setattr(wizard.subprocess, "run", lambda *a, **k: calls.append(a))

    wizard._step_install(tmp_path)

    assert calls == []


def test_step_install_runs_uv_tool_install_when_missing(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(wizard, "UV_TOOL_BIN", tmp_path / "missing" / "hyndsyght")
    calls = []
    monkeypatch.setattr(wizard.subprocess, "run", lambda *a, **k: calls.append(a))

    wizard._step_install(tmp_path)

    assert calls == [(["uv", "tool", "install", "."],)]
