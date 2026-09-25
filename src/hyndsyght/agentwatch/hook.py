"""The ONE hook entry point for every Claude Code lifecycle event.

Reads stdin JSON and appends it to the spool — no interpretation, no DB
touch, no blocking. All six lifecycle hooks (UserPromptSubmit, Stop,
StopFailure, SubagentStart, SubagentStop, SessionEnd) point at this same
command.
"""

import json
import sys
import time

import click

from hyndsyght import paths
from hyndsyght.agentwatch import spool


@click.group("agent-event")
def agent_event_group() -> None:
    """Claude Code hook plumbing."""


@agent_event_group.command("record")
def record() -> None:
    payload = json.load(sys.stdin)
    payload["_received_at"] = time.time()
    spool.append(payload, paths.spool_path())
