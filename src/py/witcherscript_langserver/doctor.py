"""Workspace health checks for the WitcherScript developer CLI."""

from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.workspace.config import (
    CONFIG_FILE_NAME,
    load_workspace_config,
    validate_workspace_config,
)


@dataclass(frozen=True)
class DoctorCheck:
    """One workspace health check result.

    Attributes:
        name: Stable check name.
        status: Check status: ``ok``, ``warning``, or ``error``.
        message: Human-readable result.
        detail: Optional additional detail.
    """

    name: str
    status: str
    message: str
    detail: str | None = None


@dataclass(frozen=True)
class DoctorReport:
    """Aggregated workspace health report.

    Attributes:
        workspace: Workspace path checked by the command.
        checks: Ordered check results.
        indexed_files: Number of indexed WitcherScript files.
        diagnostics: Number of indexed syntax and semantic diagnostics.
    """

    workspace: str
    checks: tuple[DoctorCheck, ...]
    indexed_files: int
    diagnostics: int

    @property
    def has_errors(self) -> bool:
        """Return whether any check failed."""
        return any(check.status == "error" for check in self.checks)


def run_doctor(workspace: Path) -> DoctorReport:
    """Run project health checks for a workspace.

    Args:
        workspace: Workspace root to inspect.

    Returns:
        Aggregated doctor report.
    """
    root = workspace.expanduser().resolve()
    checks: list[DoctorCheck] = []
    config_path = root / CONFIG_FILE_NAME
    indexed_files = 0
    diagnostics_count = 0

    if config_path.exists():
        checks.append(
            DoctorCheck("config.exists", "ok", "witcherscript.toml exists.", str(config_path))
        )

    else:
        checks.append(
            DoctorCheck(
                "config.exists",
                "warning",
                "witcherscript.toml is missing.",
                "Run WitcherScript: Initialize REDkit Config or ws-redkit init.",
            )
        )

    try:
        config = load_workspace_config(root)
        config_diagnostics = validate_workspace_config(config)

    except tomllib.TOMLDecodeError as error:
        checks.append(DoctorCheck("config.parse", "error", f"Invalid TOML: {error}"))
        return DoctorReport(str(root), tuple(checks), indexed_files, diagnostics_count)

    checks.append(DoctorCheck("config.parse", "ok", "Workspace configuration can be loaded."))

    for diagnostic in config_diagnostics:
        checks.append(DoctorCheck("config.paths", "error", diagnostic.message))

    if not config_diagnostics:
        checks.append(DoctorCheck("config.paths", "ok", "Configured paths are valid or optional."))

    checks.extend(_path_checks(config.redkit.game_directory, "paths.game", "Witcher 3 directory"))
    checks.extend(_path_checks(config.redkit.redkit_directory, "paths.redkit", "REDkit directory"))

    if config.scripts.vanilla_roots:
        existing_vanilla = [
            root_path for root_path in config.scripts.vanilla_roots if root_path.exists()
        ]
        status = "ok" if existing_vanilla else "error"
        message = (
            f"{len(existing_vanilla)}/{len(config.scripts.vanilla_roots)} "
            "vanilla script root(s) exist."
        )
        checks.append(
            DoctorCheck(
                "scripts.vanilla",
                status,
                message,
            )
        )
    else:
        checks.append(
            DoctorCheck(
                "scripts.vanilla",
                "warning",
                "No vanilla script roots are configured.",
            )
        )

    index = ProjectIndex.build(config)
    indexed_files = len(index.files)
    diagnostics_count = len(index.diagnostics)
    checks.append(
        DoctorCheck(
            "index.files",
            "ok" if indexed_files > 0 else "warning",
            f"Indexed {indexed_files} WitcherScript file(s).",
        )
    )
    checks.append(
        DoctorCheck(
            "index.diagnostics",
            "ok" if diagnostics_count == 0 else "warning",
            f"Detected {diagnostics_count} diagnostic(s).",
        )
    )

    checks.append(_redkit_cli_check(root))
    checks.append(_recompile_check())
    checks.append(_workspace_shape_check(root))
    return DoctorReport(str(root), tuple(checks), indexed_files, diagnostics_count)


def _path_checks(path: Path | None, name: str, label: str) -> tuple[DoctorCheck, ...]:
    if path is None:
        return (DoctorCheck(name, "warning", f"{label} is not configured."),)

    if path.exists():
        return (DoctorCheck(name, "ok", f"{label} exists.", str(path)),)

    return (DoctorCheck(name, "error", f"{label} does not exist.", str(path)),)


def _redkit_cli_check(workspace: Path) -> DoctorCheck:
    dotnet = shutil.which("dotnet")
    local_cli = (
        workspace
        / "src"
        / "dotnet"
        / "src"
        / "WitcherScript.RedkitTooling.Cli"
        / "WitcherScript.RedkitTooling.Cli.csproj"
    )

    if shutil.which("ws-redkit") is not None:
        return DoctorCheck("redkit.cli", "ok", "ws-redkit is available on PATH.")

    if dotnet is not None and local_cli.exists():
        return DoctorCheck(
            "redkit.cli",
            "ok",
            "Repository-local REDkit CLI can be run through dotnet.",
        )

    return DoctorCheck(
        "redkit.cli",
        "warning",
        "REDkit CLI was not found.",
        "Install ws-redkit or run from the repository with dotnet.",
    )


def _recompile_check() -> DoctorCheck:
    executable = os.environ.get("WITCHERSCRIPT_RECOMPILE_EXECUTABLE", "").strip()

    if not executable:
        return DoctorCheck(
            "redkit.recompile",
            "warning",
            "Recompile executable is not configured.",
            "Set WITCHERSCRIPT_RECOMPILE_EXECUTABLE or configure VS Code settings.",
        )

    path = Path(executable).expanduser()
    if path.exists():
        return DoctorCheck("redkit.recompile", "ok", "Recompile executable exists.", str(path))

    return DoctorCheck(
        "redkit.recompile",
        "error",
        "Recompile executable does not exist.",
        str(path),
    )


def _workspace_shape_check(workspace: Path) -> DoctorCheck:
    candidates = [
        workspace / "scripts",
        workspace / "content" / "scripts",
        workspace / "content",
        workspace / "Mods",
    ]

    if any(path.exists() for path in candidates):
        return DoctorCheck("workspace.shape", "ok", "Workspace looks like a script/mod project.")

    return DoctorCheck(
        "workspace.shape",
        "warning",
        "Workspace does not expose a common scripts/content/Mods layout.",
    )
