from hyndsyght.platform.macos_media import parse_osascript_output


def test_parse_osascript_output_playing_track() -> None:
    assert parse_osascript_output("playing, Sunday Morning") == (
        "playing",
        "Sunday Morning",
    )


def test_parse_osascript_output_paused_track() -> None:
    assert parse_osascript_output("paused, Kids") == ("paused", "Kids")


def test_parse_osascript_output_malformed_returns_none() -> None:
    assert parse_osascript_output("") == (None, None)
    assert parse_osascript_output("nonsense") == (None, None)
