from pathlib import Path

from hyndsyght.agentwatch.spool import append, read_new_lines, read_offset, write_offset


def test_append_then_read_new_lines(tmp_path: Path) -> None:
    spool_path = tmp_path / "spool.jsonl"
    append({"a": 1}, spool_path)
    append({"a": 2}, spool_path)

    lines, offset = read_new_lines(spool_path)
    assert len(lines) == 2
    write_offset(spool_path, offset)

    lines_again, _ = read_new_lines(spool_path)
    assert lines_again == []


def test_read_new_lines_only_returns_unread_tail(tmp_path: Path) -> None:
    spool_path = tmp_path / "spool.jsonl"
    append({"a": 1}, spool_path)
    lines, offset = read_new_lines(spool_path)
    write_offset(spool_path, offset)

    append({"a": 2}, spool_path)
    lines, _ = read_new_lines(spool_path)
    assert len(lines) == 1


def test_read_new_lines_ignores_partial_trailing_write(tmp_path: Path) -> None:
    spool_path = tmp_path / "spool.jsonl"
    append({"a": 1}, spool_path)
    with spool_path.open("a") as f:
        f.write('{"a": 2}')  # no trailing newline — partial write

    lines, offset = read_new_lines(spool_path)
    assert len(lines) == 1
    assert offset == read_offset(spool_path) + len(lines[0])
