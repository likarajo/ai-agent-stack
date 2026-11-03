"""Read a plugin manifest and 'install' it into a local host config.

A plugin is packaging/distribution — not a new wire protocol. Once installed,
work still flows through tools, MCP, skills, and APIs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PLUGIN = (
    ROOT / "05-plugins" / "plugin" / "northwind-issue-tracker" / "plugin.json"
)
INSTALL_DIR = ROOT / "05-plugins" / ".installed"


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["name", "version", "mcp_servers", "skills", "commands"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"plugin manifest missing keys: {missing}")
    return data


def install_plugin(manifest_path: Path, install_dir: Path = INSTALL_DIR) -> Path:
    manifest = load_manifest(manifest_path)
    install_dir.mkdir(parents=True, exist_ok=True)
    target = install_dir / f"{manifest['name']}.json"
    # Resolve relative paths against repo root for the installed host config.
    resolved = {
        **manifest,
        "source_manifest": str(manifest_path.resolve()),
        "mcp_servers": [
            {
                **server,
                "args": [
                    str((ROOT / arg).resolve()) if not arg.startswith("-") and "/" in arg else arg
                    for arg in server.get("args", [])
                ],
            }
            for server in manifest["mcp_servers"]
        ],
        "skills": [str((ROOT / s).resolve()) for s in manifest["skills"]],
    }
    target.write_text(json.dumps(resolved, indent=2) + "\n", encoding="utf-8")
    return target


def describe_install(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"Installed plugin: {data['display_name']} ({data['name']}@{data['version']})",
        f"MCP servers: {', '.join(s['name'] for s in data['mcp_servers'])}",
        f"Skills: {', '.join(Path(s).name for s in data['skills'])}",
        f"Commands: {', '.join(c['name'] for c in data['commands'])}",
        "Key point: packaging only — runtime still uses MCP/tools/skills/APIs.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install a local AI plugin bundle")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_PLUGIN)
    args = parser.parse_args()
    target = install_plugin(args.manifest)
    print(describe_install(target))
    print(f"\nWrote host config → {target}")


if __name__ == "__main__":
    main()
