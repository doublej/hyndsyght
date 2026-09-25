from pathlib import Path

from hyndsyght.api.auth import ensure_token


def test_ensure_token_writes_once_and_is_owner_only(tmp_path: Path) -> None:
    path = tmp_path / "api-token"
    token = ensure_token(path)
    assert ensure_token(path) == token
    assert oct(path.stat().st_mode)[-3:] == "600"
