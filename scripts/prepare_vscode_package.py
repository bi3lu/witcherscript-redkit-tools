"""Prepare bundled assets for packaging the VS Code extension."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VSCODE_ROOT = ROOT / "src" / "vscode"
SERVER_BUNDLE = VSCODE_ROOT / "server"
REDKIT_BUNDLE = VSCODE_ROOT / "redkit"
VSCODE_LICENSE = VSCODE_ROOT / "LICENSE"


def main() -> None:
    """Create clean VS Code extension bundles for Python and REDkit tooling."""
    _reset_directory(SERVER_BUNDLE)
    _reset_directory(REDKIT_BUNDLE)
    (ROOT / "dist").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "LICENSE", VSCODE_LICENSE)
    _bundle_python_server()
    _bundle_redkit_tooling()


def _bundle_python_server() -> None:
    for name in ("LICENSE", "README.md", "VERSION", "pyproject.toml", "uv.lock"):
        shutil.copy2(ROOT / name, SERVER_BUNDLE / name)

    shutil.copytree(
        ROOT / "src" / "py",
        SERVER_BUNDLE / "src" / "py",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )


def _bundle_redkit_tooling() -> None:
    dotnet_root = ROOT / "src" / "dotnet"

    for name in ("Directory.Build.props", "Directory.Packages.props", "NuGet.config"):
        source = dotnet_root / name

        if source.exists():
            shutil.copy2(source, REDKIT_BUNDLE / name)

    target_src = REDKIT_BUNDLE / "src"
    target_src.mkdir(parents=True, exist_ok=True)

    for project_name in (
        "WitcherScript.RedkitTooling",
        "WitcherScript.RedkitTooling.Cli",
    ):
        shutil.copytree(
            dotnet_root / "src" / project_name,
            target_src / project_name,
            ignore=shutil.ignore_patterns("bin", "obj", "*.user"),
        )


def _reset_directory(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)

    path.mkdir(parents=True)


if __name__ == "__main__":
    main()
