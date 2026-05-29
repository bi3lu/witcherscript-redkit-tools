"""Project-wide WitcherScript file index."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from witcherscript_langserver.config import WorkspaceConfig
from witcherscript_langserver.indexing.file_index import FileIndex, IndexedSymbol, build_file_index
from witcherscript_langserver.parser.errors import SyntaxDiagnostic


@dataclass
class ProjectIndex:
    """Mutable index of parsed WitcherScript files in a workspace.

    Attributes:
        files: Mapping from local file path to per-file index data.
    """

    files: dict[Path, FileIndex] = field(default_factory=dict)

    @classmethod
    def build(cls, config: WorkspaceConfig) -> ProjectIndex:
        """Scan configured roots and build a project index.

        Args:
            config: Resolved workspace configuration.

        Returns:
            Project index containing every discovered ``.ws`` file that is not excluded.
        """
        index = cls()

        for path in scan_script_files(config):
            index.index_path(path)

        return index

    def index_path(self, path: Path, source: str | None = None) -> FileIndex:
        """Index or reindex a single WitcherScript file.

        Args:
            path: Local file path.
            source: Optional source text. When omitted, the file is read from disk.

        Returns:
            New per-file index.
        """
        resolved_path = path.expanduser().resolve()
        text = source if source is not None else resolved_path.read_text(encoding="utf-8")
        file_index = build_file_index(resolved_path, resolved_path.as_uri(), text)
        self.files[resolved_path] = file_index
        return file_index

    def remove_path(self, path: Path) -> None:
        """Remove a file from the project index.

        Args:
            path: Local file path to remove.
        """
        self.files.pop(path.expanduser().resolve(), None)

    @property
    def symbols(self) -> tuple[IndexedSymbol, ...]:
        """Return all indexed symbols in project order.

        Returns:
            Flattened symbols from every indexed file.
        """
        return tuple(symbol for file in self.files.values() for symbol in file.symbols)

    @property
    def diagnostics(self) -> tuple[SyntaxDiagnostic, ...]:
        """Return all indexed syntax diagnostics in project order.

        Returns:
            Flattened diagnostics from every indexed file.
        """
        return tuple(diagnostic for file in self.files.values() for diagnostic in file.diagnostics)


def scan_script_files(config: WorkspaceConfig) -> tuple[Path, ...]:
    """Find WitcherScript files for a workspace configuration.

    Args:
        config: Resolved workspace configuration.

    Returns:
        Sorted local paths to discovered ``.ws`` files.
    """
    discovered: set[Path] = set()

    for root in config.script_roots:
        if not root.exists():
            continue

        candidates = (root,) if root.is_file() else root.rglob("*.ws")

        for candidate in candidates:
            path = candidate.expanduser().resolve()

            if path.suffix.lower() != ".ws" or _is_excluded(path, root, config):
                continue

            discovered.add(path)

    return tuple(sorted(discovered))


def _is_excluded(path: Path, script_root: Path, config: WorkspaceConfig) -> bool:
    candidates = {
        _relative_posix(path, config.root_path),
        _relative_posix(path, script_root),
        path.as_posix(),
    }

    return any(
        _matches_pattern(candidate, pattern)
        for candidate in candidates
        for pattern in config.scripts.exclude
    )


def _relative_posix(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()

    except ValueError:
        return path.as_posix()


def _matches_pattern(candidate: str, pattern: str) -> bool:
    normalized = pattern.replace("\\", "/")

    if fnmatch(candidate, normalized):
        return True

    return normalized.startswith("**/") and fnmatch(candidate, normalized[3:])
