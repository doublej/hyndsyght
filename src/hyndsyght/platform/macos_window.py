"""Frontmost app + window title, and the app icons the dashboard shows.

Reading window titles needs Screen Recording permission granted to the
terminal/binary running hyndsyght — document it, don't code around it.
"""

from functools import lru_cache

import Quartz
from AppKit import (
    NSBitmapImageFileTypePNG,
    NSBitmapImageRep,
    NSDeviceRGBColorSpace,
    NSGraphicsContext,
    NSRunningApplication,
    NSWorkspace,
)

from hyndsyght.platform.types import Event

_LIST_OPTIONS = (
    Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
)


class MacWindowWatcher:
    def poll(self) -> Event | None:
        app_name, title, pid = pick_frontmost(
            Quartz.CGWindowListCopyWindowInfo(_LIST_OPTIONS, Quartz.kCGNullWindowID)
        )
        if app_name is None:
            return None
        payload = {"app": app_name}
        if bundle := bundle_path(pid):
            payload["bundle"] = bundle
        return Event(kind="window", title=title or app_name, payload=payload)


def bundle_path(pid: int | None) -> str | None:
    """The .app bundle behind a process, so the dashboard can show its icon.

    Looked up by pid rather than name: a process name ("iTerm2") need not
    match its bundle ("iTerm.app").
    """
    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid or -1)
    url = app.bundleURL() if app else None
    path = str(url.path()) if url else None
    return path if path and path.endswith(".app") else None


def pick_frontmost(windows: list[dict]) -> tuple[str | None, str | None, int | None]:
    """First on-screen layer-0 window — the window list is ordered front to back.

    NSWorkspace.frontmostApplication() is the obvious API and the wrong one: it
    caches, and a daemon with no run loop to pump never sees the value change.
    """
    for window in windows:
        if window.get("kCGWindowLayer") != 0:
            continue
        owner = window.get("kCGWindowOwnerName")
        if not owner:
            continue
        name = window.get("kCGWindowName")
        pid = window.get("kCGWindowOwnerPID")
        return str(owner), str(name) if name else None, pid
    return None, None, None


def find_bundle(app_name: str) -> str | None:
    """Launch Services lookup by name; misses apps whose process name differs."""
    path = NSWorkspace.sharedWorkspace().fullPathForApplication_(app_name)
    return str(path) if path else None


@lru_cache(maxsize=128)
def icon_png(bundle: str, size: int) -> bytes:
    icon = NSWorkspace.sharedWorkspace().iconForFile_(bundle)
    rep = NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
        None, size, size, 8, 4, True, False, NSDeviceRGBColorSpace, 0, 0
    )
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.setCurrentContext_(
        NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep)
    )
    icon.drawInRect_(((0, 0), (size, size)))
    NSGraphicsContext.restoreGraphicsState()
    return bytes(rep.representationUsingType_properties_(NSBitmapImageFileTypePNG, {}))
