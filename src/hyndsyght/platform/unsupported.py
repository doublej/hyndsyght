"""Stub watcher for platforms without a backend yet (Windows, Linux)."""

from hyndsyght.platform.types import Event


class UnsupportedWatcher:
    def poll(self) -> Event | None:
        raise NotImplementedError("hyndsyght only supports macOS right now")
