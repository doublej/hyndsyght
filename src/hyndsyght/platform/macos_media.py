"""Spotify/Music playback state.

Checks whether the app is actually running before ever shelling out to
AppleScript — `osascript -e 'tell application "Spotify" to ...'` launches
the app if it isn't running, which a passive tracker must never do.
"""

import subprocess

from AppKit import NSWorkspace

from hyndsyght.platform.types import Event

_BUNDLE_IDS = {"com.spotify.client": "Spotify", "com.apple.Music": "Music"}


class MacMediaWatcher:
    def poll(self) -> Event | None:
        app_name = _running_media_app()
        if app_name is None:
            return None
        script = f'tell application "{app_name}" to get {{player state, name of current track}}'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return None
        state, track = parse_osascript_output(result.stdout)
        if state is None:
            return None
        return Event(kind=state, title=track, payload={"app": app_name})


def _running_media_app() -> str | None:
    running_bundle_ids = {
        app.bundleIdentifier()
        for app in NSWorkspace.sharedWorkspace().runningApplications()
    }
    for bundle_id, name in _BUNDLE_IDS.items():
        if bundle_id in running_bundle_ids:
            return name
    return None


def parse_osascript_output(output: str) -> tuple[str | None, str | None]:
    """Parse `{player state, name of current track}` -> (state, track)."""
    parts = [p.strip() for p in output.strip().split(",", 1)]
    if len(parts) != 2 or not parts[0]:
        return None, None
    return parts[0], parts[1]
