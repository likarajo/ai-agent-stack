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

_PYTHON_COMMANDS = frozenset({"python", "python3", "py"})


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ["name", "version", "mcp_servers", "skills", "commands"]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"plugin manifest missing keys: {missing}")
    return data


def _resolve_command(command: str) -> str:
    """Resolve interpreter names to this process's executable (no PATH needed)."""
    if command in _PYTHON_COMMANDS:
        return sys.executable
    # Absolute commands pass through; bare names stay as-is for non-Python tools.
    candidate = Path(command)
    if candidate.is_absolute():
        return str(candidate)
    return command


def _resolve_arg(arg: str, *, module_root: Path) -> str:
    """Resolve relative file paths against the repo root (or keep flags/values)."""
    if arg.startswith("-") or arg.startswith("="):
        return arg
    # Paths in the manifest are repo-root relative (e.g. 04-mcp/server/...).
    if "/" in arg or arg.endswith(".py"):
        path = Path(arg)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
            if not path.exists():
                # Fall back to module-relative resolution for portable bundles.
                alt = (module_root / arg).resolve()
                if alt.exists():
                    path = alt
        return str(path)
    return arg


def install_plugin(manifest_path: Path, install_dir: Path = INSTALL_DIR) -> Path:
    manifest = load_manifest(manifest_path)
    install_dir.mkdir(parents=True, exist_ok=True)
    target = install_dir / f"{manifest['name']}.json"
    module_root = manifest_path.resolve().parents[2]  # .../05-plugins
    # Resolve command + relative paths so the host config works without PATH tweaks.
    resolved = {
        **manifest,
        "source_manifest": str(manifest_path.resolve()),
        "mcp_servers": [
            {
                **server,
                "command": _resolve_command(server.get("command", "python")),
                "args": [
                    _resolve_arg(arg, module_root=module_root)
                    for arg in server.get("args", [])
                ],
                "cwd": str(ROOT),
                "env": {
                    **server.get("env", {}),
                    "PYTHONPATH": server.get("env", {}).get("PYTHONPATH")
                    or f"{ROOT}:{ROOT / '04-mcp'}",
                },
            }
            for server in manifest["mcp_servers"]
        ],
        "skills": [
            str((ROOT / s).resolve()) if not Path(s).is_absolute() else s
            for s in manifest["skills"]
        ],
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
