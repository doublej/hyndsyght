"""launchd plist generation + service lifecycle + optional project-atlas registration.

The plist is a generated artifact (mirrors categorize/rules.py's TEMPLATE
pattern) — it embeds the actual repo root and home dir, so it works for any
clone rather than baking in one machine's paths.
"""

import json
import subprocess
from pathlib import Path

PLIST_LABEL = "com.hyndsyght.daemon"

# Daemon: always restart. Tray: restart only after a crash, so Quit stays quit.
KEEP_ALIVE = {
    "daemon": "<true/>",
    "tray": "<dict>\n\t\t<key>SuccessfulExit</key>\n\t\t<false/>\n\t</dict>",
}
# The tray needs a GUI session to draw its menu-bar icon.
SESSION_TYPE = {
    "daemon": "",
    "tray": "\t<key>LimitLoadToSessionType</key>\n\t<string>Aqua</string>\n",
}

PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>Label</key>
\t<string>{label}</string>

\t<key>ProgramArguments</key>
\t<array>
\t\t<string>{repo_root}/.venv/bin/hyndsyght</string>
\t\t<string>{command}</string>
\t</array>

\t<key>RunAtLoad</key>
\t<true/>
\t<key>KeepAlive</key>
\t{keep_alive}
{session_type}
\t<key>StandardOutPath</key>
\t<string>{home}/Library/Logs/hyndsyght/{command}.out.log</string>
\t<key>StandardErrorPath</key>
\t<string>{home}/Library/Logs/hyndsyght/{command}.err.log</string>

\t<key>EnvironmentVariables</key>
\t<dict>
\t\t<key>HOME</key>
\t\t<string>{home}</string>
\t\t<key>PATH</key>
\t\t<string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
\t</dict>
</dict>
</plist>
"""

# ponytail: owner's personal cross-project daemon registry; no-ops on any
# other machine since the path simply won't exist there.
ATLAS_DAEMONS_PATH = (
    Path.home() / "dev" / "multi-stack" / "project-atlas" / "shared" / "daemons.json"
)


def label_for(command: str) -> str:
    return f"com.hyndsyght.{command}"


def ensure_plist(
    repo_root: Path, home: Path | None = None, command: str = "daemon"
) -> Path:
    home = home or Path.home()
    plist_path = repo_root / "launchd" / f"{label_for(command)}.plist"
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    plist_path.write_text(
        PLIST_TEMPLATE.format(
            label=label_for(command),
            command=command,
            keep_alive=KEEP_ALIVE[command],
            session_type=SESSION_TYPE[command],
            repo_root=repo_root,
            home=home,
        )
    )
    return plist_path


def service_install(repo_root: Path, command: str = "daemon") -> bool:
    ensure_plist(repo_root, command=command)
    (Path.home() / "Library" / "Logs" / "hyndsyght").mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["just", "service-install", command], cwd=repo_root, check=False
    )
    return result.returncode == 0


def register_in_atlas(repo_root: Path, command: str = "daemon") -> str:
    if not ATLAS_DAEMONS_PATH.exists():
        return "project-atlas not found — skipped"
    data = json.loads(ATLAS_DAEMONS_PATH.read_text())
    daemons = data.setdefault("daemons", [])
    label = label_for(command)
    if any(d.get("label") == label for d in daemons):
        return "already registered in project-atlas"
    daemons.append(
        {
            "label": label,
            "name": "hyndsyght" if command == "daemon" else f"hyndsyght {command}",
            "project": str(repo_root),
            "plist": str(repo_root / "launchd" / f"{label}.plist"),
            "logs": {
                "stdout": f"~/Library/Logs/hyndsyght/{command}.out.log",
                "stderr": f"~/Library/Logs/hyndsyght/{command}.err.log",
            },
        }
    )
    ATLAS_DAEMONS_PATH.write_text(json.dumps(data, indent=2) + "\n")
    return "registered in project-atlas"
