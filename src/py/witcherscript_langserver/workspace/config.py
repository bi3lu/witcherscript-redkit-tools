"""Workspace configuration loading for ``witcherscript.toml``."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_FILE_NAME = "witcherscript.toml"
DEFAULT_SOURCE_ROOTS = (".",)
DEFAULT_EXCLUDE_PATTERNS = (
    "**/bin/**",
    "**/.cache/**",
    "**/.ws-cache/**",
    "**/generated/**",
)


@dataclass(frozen=True)
class ProjectConfig:
    """Project metadata from ``witcherscript.toml``.

    Attributes:
        name: Human-readable project name.
    """

    name: str


@dataclass(frozen=True)
class RedkitConfig:
    """REDkit path configuration.

    Attributes:
        game_directory: Optional The Witcher 3 installation directory.
        redkit_directory: Optional REDkit installation directory.
        project_directory: Optional REDkit project directory.
    """

    game_directory: Path | None = None
    redkit_directory: Path | None = None
    project_directory: Path | None = None


@dataclass(frozen=True)
class ScriptsConfig:
    """Script discovery configuration.

    Attributes:
        source_roots: Project script roots.
        vanilla_roots: Vanilla game script roots.
        exclude: Glob-like patterns ignored while scanning.
    """

    source_roots: tuple[Path, ...]
    vanilla_roots: tuple[Path, ...] = field(default_factory=tuple)
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE_PATTERNS


@dataclass(frozen=True)
class WorkspaceConfig:
    """Resolved workspace configuration.

    Attributes:
        root_path: Workspace root directory.
        config_path: Path to ``witcherscript.toml``, when one was found.
        project: Project metadata.
        redkit: REDkit path configuration.
        scripts: Script discovery configuration.
    """

    root_path: Path
    config_path: Path | None
    project: ProjectConfig
    redkit: RedkitConfig
    scripts: ScriptsConfig

    @property
    def script_roots(self) -> tuple[Path, ...]:
        """Return all configured roots that should be scanned for ``.ws`` files.

        Returns:
            Project and vanilla script roots in discovery order.
        """
        return (*self.scripts.source_roots, *self.scripts.vanilla_roots)


def load_workspace_config(root_path: Path) -> WorkspaceConfig:
    """Load and resolve a workspace configuration.

    Args:
        root_path: Workspace root directory received from the LSP client.

    Returns:
        Resolved workspace configuration. Missing config files fall back to a
        conservative root-based project model.
    """
    root = root_path.expanduser().resolve()
    config_path = root / CONFIG_FILE_NAME

    if not config_path.exists():
        return _default_config(root)

    with config_path.open("rb") as config_file:
        data = tomllib.load(config_file)

    project_section = _mapping_section(data, "project")
    redkit_section = _mapping_section(data, "redkit")
    scripts_section = _mapping_section(data, "scripts")

    source_roots = _path_sequence(
        scripts_section.get("source_roots"),
        root,
        default=DEFAULT_SOURCE_ROOTS,
    )
    vanilla_roots = _path_sequence(scripts_section.get("vanilla_roots"), root, default=())
    exclude = _string_sequence(
        scripts_section.get("exclude"),
        default=DEFAULT_EXCLUDE_PATTERNS,
    )

    return WorkspaceConfig(
        root_path=root,
        config_path=config_path,
        project=ProjectConfig(name=_string_value(project_section.get("name"), root.name)),
        redkit=RedkitConfig(
            game_directory=_optional_path(redkit_section.get("game_directory"), root),
            redkit_directory=_optional_path(redkit_section.get("redkit_directory"), root),
            project_directory=_optional_path(redkit_section.get("project_directory"), root),
        ),
        scripts=ScriptsConfig(
            source_roots=source_roots,
            vanilla_roots=vanilla_roots,
            exclude=exclude,
        ),
    )


def _default_config(root: Path) -> WorkspaceConfig:
    return WorkspaceConfig(
        root_path=root,
        config_path=None,
        project=ProjectConfig(name=root.name),
        redkit=RedkitConfig(),
        scripts=ScriptsConfig(
            source_roots=(_resolve_path(".", root),),
            exclude=DEFAULT_EXCLUDE_PATTERNS,
        ),
    )


def _mapping_section(data: Mapping[str, object], section_name: str) -> Mapping[str, object]:
    value = data.get(section_name)
    if isinstance(value, Mapping):
        return value

    return {}


def _path_sequence(value: object, root: Path, *, default: Sequence[str]) -> tuple[Path, ...]:
    return tuple(_resolve_path(item, root) for item in _string_sequence(value, default=default))


def _string_sequence(value: object, *, default: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str):
        return tuple(default)

    return tuple(item for item in value if isinstance(item, str))


def _optional_path(value: object, root: Path) -> Path | None:
    if not isinstance(value, str) or not value:
        return None

    return _resolve_path(value, root)


def _resolve_path(value: str, root: Path) -> Path:
    path = Path(value).expanduser()

    if not path.is_absolute():
        path = root / path

    return path.resolve()


def _string_value(value: object, default: str) -> str:
    if isinstance(value, str) and value:
        return value

    return default
