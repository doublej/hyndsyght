"""AFK detection via seconds-since-last-HID-event — one Quartz call."""

import Quartz

from hyndsyght.platform.types import Event

AFK_THRESHOLD_SECONDS = (
    300  # ponytail: fixed threshold, make configurable if it ever needs tuning
)


class MacAfkWatcher:
    def poll(self) -> Event | None:
        idle_seconds = Quartz.CGEventSourceSecondsSinceLastEventType(
            Quartz.kCGEventSourceStateHIDSystemState, Quartz.kCGAnyInputEventType
        )
        kind = "afk" if idle_seconds >= AFK_THRESHOLD_SECONDS else "active"
        return Event(kind=kind, title=None, payload={"idle_seconds": idle_seconds})
