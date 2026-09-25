"""The menu-bar app: an NSStatusItem whose menu is rebuilt from `model` on
every open, plus the dashboard server on a background thread.
"""

import os
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSMenu,
    NSMenuItem,
    NSObject,
    NSStatusBar,
    NSTimer,
    NSVariableStatusItemLength,
)
from PyObjCTools import AppHelper

from hyndsyght import daemon
from hyndsyght import status as status_module
from hyndsyght.api.app import create_app
from hyndsyght.setup.daemon import PLIST_LABEL
from hyndsyght.status import SCREEN_RECORDING_PANE_URL
from hyndsyght.tray import model

ICON_REFRESH_SECONDS = 60.0
PAUSE_SECONDS = {"pause_15m": 15 * 60, "pause_1h": 3600, "pause_forever": float("inf")}


class TrayController(NSObject):  # type: ignore[misc]
    def initWithLocale_port_(self, locale: str, port: int) -> "TrayController":
        self = self.init()  # noqa: PLW0642 - PyObjC init convention
        self.locale, self.port = locale, port
        self.item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSVariableStatusItemLength
        )
        menu = NSMenu.alloc().init()
        menu.setAutoenablesItems_(False)
        menu.setDelegate_(self)
        self.item.setMenu_(menu)
        self.refreshIcon_(None)
        return self

    def menuNeedsUpdate_(self, menu: NSMenu) -> None:
        now = time.time()
        menu.removeAllItems()
        for item in model.menu_items(model.snapshot(now), self.locale, now):
            menu.addItem_(build_menu_item(item, self))

    def perform_(self, sender: NSMenuItem) -> None:
        action = sender.representedObject()
        if action in PAUSE_SECONDS:
            daemon.set_pause(time.time() + PAUSE_SECONDS[action])
        elif action == "resume":
            daemon.set_pause(None)
        elif action == "open":
            webbrowser.open(f"http://127.0.0.1:{self.port}")
        elif action == "open_permission":
            subprocess.run(["open", SCREEN_RECORDING_PANE_URL], check=False)
        elif action == "restart_daemon":
            restart_daemon()
        elif action == "quit":
            NSApplication.sharedApplication().terminate_(None)
        self.refreshIcon_(None)

    def refreshIcon_(self, _timer: NSTimer | None) -> None:
        name = model.icon_name(
            status_module.report()["daemon_running"],
            time.time() < daemon.paused_until(),
        )
        image = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
            name, "hyndsyght"
        )
        image.setTemplate_(True)
        self.item.button().setImage_(image)


def build_menu_item(item: model.Item, target: NSObject) -> NSMenuItem:
    if item == model.SEPARATOR:
        return NSMenuItem.separatorItem()
    entry = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
        item.label, "perform:" if item.action else None, ""
    )
    entry.setTarget_(target)
    entry.setRepresentedObject_(item.action)
    entry.setEnabled_(item.enabled)
    if item.children:
        submenu = NSMenu.alloc().init()
        for child in item.children:
            submenu.addItem_(build_menu_item(child, target))
        entry.setSubmenu_(submenu)
    return entry


def restart_daemon() -> None:
    """Bootstrap first: after `service-stop` the agent is unloaded and kickstart alone fails."""
    domain = f"gui/{os.getuid()}"
    agent = Path.home() / "Library" / "LaunchAgents" / f"{PLIST_LABEL}.plist"
    subprocess.run(["launchctl", "bootstrap", domain, str(agent)], check=False)
    subprocess.run(
        ["launchctl", "kickstart", "-k", f"{domain}/{PLIST_LABEL}"], check=False
    )


def run(locale: str, port: int) -> None:
    config = uvicorn.Config(create_app(port), host="127.0.0.1", port=port)
    threading.Thread(target=uvicorn.Server(config).run, daemon=True).start()
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = TrayController.alloc().initWithLocale_port_(locale, port)
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        ICON_REFRESH_SECONDS, controller, "refreshIcon:", None, True
    )
    AppHelper.runEventLoop(installInterrupt=True)
