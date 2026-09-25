"""Platform-abstraction seam: Protocols + factories dispatching on sys.platform.

macOS backends only for now — Windows/Linux fall back to unsupported.py stubs.
Cadence and orchestration are the daemon's job; each watcher only exposes a
plain, stateless poll().
"""

import sys
from typing import Protocol

from hyndsyght.platform.types import Event


class WindowWatcher(Protocol):
    def poll(self) -> Event | None: ...


class AfkWatcher(Protocol):
    def poll(self) -> Event | None: ...


class MediaWatcher(Protocol):
    def poll(self) -> Event | None: ...


def window_watcher() -> WindowWatcher:
    if sys.platform == "darwin":
        from hyndsyght.platform.macos_window import MacWindowWatcher

        return MacWindowWatcher()
    from hyndsyght.platform.unsupported import UnsupportedWatcher

    return UnsupportedWatcher()


def afk_watcher() -> AfkWatcher:
    if sys.platform == "darwin":
        from hyndsyght.platform.macos_afk import MacAfkWatcher

        return MacAfkWatcher()
    from hyndsyght.platform.unsupported import UnsupportedWatcher

    return UnsupportedWatcher()


def media_watcher() -> MediaWatcher:
    if sys.platform == "darwin":
        from hyndsyght.platform.macos_media import MacMediaWatcher

        return MacMediaWatcher()
    from hyndsyght.platform.unsupported import UnsupportedWatcher

    return UnsupportedWatcher()


def app_icon(app_name: str, bundle: str | None, size: int) -> bytes | None:
    """PNG icon for an app, or None where it can't be found or drawn."""
    if sys.platform != "darwin":
        return None
    from hyndsyght.platform import macos_window

    path = bundle or macos_window.find_bundle(app_name)
    return macos_window.icon_png(path, size) if path else None
