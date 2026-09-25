from hyndsyght.platform.macos_window import pick_frontmost


def _window(owner: str | None, name: str | None, layer: int = 0) -> dict:
    return {
        "kCGWindowOwnerName": owner,
        "kCGWindowName": name,
        "kCGWindowLayer": layer,
    }


def test_pick_frontmost_takes_first_layer_zero_window() -> None:
    windows = [_window("Chrome", "Inbox"), _window("iTerm2", "zsh")]
    assert pick_frontmost(windows) == ("Chrome", "Inbox", None)


def test_pick_frontmost_skips_menubar_and_overlay_layers() -> None:
    windows = [
        _window("Window Server", "Menubar", layer=25),
        _window("Chrome", "Inbox"),
    ]
    assert pick_frontmost(windows) == ("Chrome", "Inbox", None)


def test_pick_frontmost_without_screen_recording_permission_has_no_title() -> None:
    assert pick_frontmost([_window("Chrome", None)]) == ("Chrome", None, None)


def test_pick_frontmost_on_empty_list_returns_nothing() -> None:
    assert pick_frontmost([]) == (None, None, None)
