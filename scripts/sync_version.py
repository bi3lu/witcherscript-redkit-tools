"""Synchronize package metadata versions from the repository VERSION file."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "VERSION"


def main() -> None:
    """Run the version synchronization command."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when synchronized files do not match VERSION.",
    )
    args = parser.parse_args()

    version = VERSION_FILE.read_text(encoding="utf-8").strip()
    changed = [
        _sync_pyproject(version, check=args.check),
        _sync_python_package(version, check=args.check),
        _sync_python_cli(version, check=args.check),
        _sync_vscode_package(version, check=args.check),
        _sync_vscode_lockfile(version, check=args.check),
        _sync_dotnet_props(version, check=args.check),
    ]

    if args.check and any(changed):
        raise SystemExit("Version metadata is out of sync. Run: python scripts/sync_version.py")


def _sync_pyproject(version: str, *, check: bool) -> bool:
    path = ROOT / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    updated = re.sub(r'(?m)^version = "[^"]+"$', f'version = "{version}"', text, count=1)
    return _write_if_changed(path, text, updated, check=check)


def _sync_python_package(version: str, *, check: bool) -> bool:
    path = ROOT / "src" / "py" / "witcherscript_langserver" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    updated = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"', text, count=1)
    return _write_if_changed(path, text, updated, check=check)


def _sync_python_cli(version: str, *, check: bool) -> bool:
    path = ROOT / "src" / "py" / "witcherscript_cli" / "main.py"
    text = path.read_text(encoding="utf-8")
    updated = re.sub(
        r'click\.echo\("witcherscript [^"]+"\)',
        f'click.echo("witcherscript {version}")',
        text,
        count=1,
    )
    return _write_if_changed(path, text, updated, check=check)


def _sync_vscode_package(version: str, *, check: bool) -> bool:
    return _sync_json_version(ROOT / "src" / "vscode" / "package.json", version, check=check)


def _sync_vscode_lockfile(version: str, *, check: bool) -> bool:
    path = ROOT / "src" / "vscode" / "package-lock.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["version"] = version
    package = data.get("packages", {}).get("")

    if isinstance(package, dict):
        package["version"] = version

    updated = json.dumps(data, indent=2) + "\n"
    return _write_if_changed(path, path.read_text(encoding="utf-8"), updated, check=check)


def _sync_json_version(path: Path, version: str, *, check: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    data["version"] = version
    updated = json.dumps(data, indent=2) + "\n"
    return _write_if_changed(path, text, updated, check=check)


def _sync_dotnet_props(version: str, *, check: bool) -> bool:
    path = ROOT / "src" / "dotnet" / "Directory.Build.props"
    text = path.read_text(encoding="utf-8")
    updated = re.sub(r"<Version>[^<]+</Version>", f"<Version>{version}</Version>", text, count=1)
    updated = re.sub(
        r"<AssemblyVersion>[^<]+</AssemblyVersion>",
        f"<AssemblyVersion>{version}</AssemblyVersion>",
        updated,
        count=1,
    )
    updated = re.sub(
        r"<FileVersion>[^<]+</FileVersion>",
        f"<FileVersion>{version}</FileVersion>",
        updated,
        count=1,
    )
    return _write_if_changed(path, text, updated, check=check)


def _write_if_changed(path: Path, original: str, updated: str, *, check: bool) -> bool:
    changed = original != updated

    if changed and not check:
        path.write_text(updated, encoding="utf-8")

    return changed


if __name__ == "__main__":
    main()
