"""Project-wide WitcherScript file index."""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from witcherscript_langserver.analysis.diagnostics_rules import (
    SemanticDiagnosticSet,
    collect_semantic_diagnostics,
)
from witcherscript_langserver.analysis.inheritance import InheritanceIndex
from witcherscript_langserver.analysis.symbol_table import Scope, Symbol, SymbolTable, TypeReference
from witcherscript_langserver.indexing.file_index import FileIndex, build_file_index
from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.workspace.config import WorkspaceConfig


@dataclass
class ProjectIndex:
    """Mutable index of parsed WitcherScript files in a workspace.

    Attributes:
        files: Mapping from local file path to per-file index data.
        symbol_table: Project-wide symbol table rebuilt after index changes.
        inheritance_index: Class inheritance lookup rebuilt after index changes.
        semantic_diagnostics: Project semantic diagnostics grouped by file URI.
    """

    files: dict[Path, FileIndex] = field(default_factory=dict)
    symbol_table: SymbolTable = field(default_factory=lambda: SymbolTable.build((), (), ()))
    inheritance_index: InheritanceIndex = field(default_factory=lambda: InheritanceIndex.build(()))
    semantic_diagnostics: SemanticDiagnosticSet = field(
        default_factory=lambda: SemanticDiagnosticSet({})
    )

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
        self._rebuild_symbol_tables()
        return file_index

    def remove_path(self, path: Path) -> None:
        """Remove a file from the project index.

        Args:
            path: Local file path to remove.
        """
        self.files.pop(path.expanduser().resolve(), None)
        self._rebuild_symbol_tables()

    @property
    def symbols(self) -> tuple[Symbol, ...]:
        """Return all indexed symbols in project order.

        Returns:
            Flattened symbols from every indexed file.
        """
        return self.symbol_table.symbols

    @property
    def scopes(self) -> tuple[Scope, ...]:
        """Return all indexed scopes in project order.

        Returns:
            Flattened scopes from every indexed file.
        """
        return self.symbol_table.scopes

    @property
    def type_references(self) -> tuple[TypeReference, ...]:
        """Return all indexed type references in project order.

        Returns:
            Flattened type references from every indexed file.
        """
        return self.symbol_table.type_references

    @property
    def diagnostics(self) -> tuple[SyntaxDiagnostic, ...]:
        """Return all indexed diagnostics in project order.

        Returns:
            Flattened syntax and semantic diagnostics from every indexed file.
        """
        return tuple(
            diagnostic
            for file in self.files.values()
            for diagnostic in (*file.diagnostics, *self.semantic_diagnostics.for_file(file.uri))
        )

    def diagnostics_for_uri(self, file_uri: str) -> tuple[SyntaxDiagnostic, ...]:
        """Return indexed diagnostics for a file URI.

        Args:
            file_uri: LSP file URI.

        Returns:
            Syntax and semantic diagnostics for the file.
        """
        for file in self.files.values():
            if file.uri == file_uri:
                return (*file.diagnostics, *self.semantic_diagnostics.for_file(file_uri))

        return self.semantic_diagnostics.for_file(file_uri)

    @property
    def imports(self) -> tuple[tuple[str, str], ...]:
        """Return import targets by declaring file.

        Returns:
            Pairs of declaring file URI and import target.
        """
        return tuple((file.uri, target) for file in self.files.values() for target in file.imports)

    def resolve_import(self, import_target: str) -> FileIndex | None:
        """Resolve an import target to an indexed file when possible.

        Args:
            import_target: Import target as written in source or without quotes.

        Returns:
            Matching file index, or ``None`` when the target cannot be resolved.
        """
        normalized = _normalize_import_target(import_target)

        for file in self.files.values():
            if _matches_import_target(file.path, normalized):
                return file

        return None

    def _rebuild_symbol_tables(self) -> None:
        symbols = tuple(symbol for file in self.files.values() for symbol in file.symbols)
        scopes = tuple(scope for file in self.files.values() for scope in file.scopes)
        type_references = tuple(
            reference for file in self.files.values() for reference in file.type_references
        )
        callable_signatures = tuple(
            signature for file in self.files.values() for signature in file.callable_signatures
        )
        self.symbol_table = SymbolTable.build(
            symbols,
            scopes,
            type_references,
            callable_signatures,
        )
        self.inheritance_index = InheritanceIndex.build(symbols)
        self.semantic_diagnostics = collect_semantic_diagnostics(
            tuple(self.files.values()),
            self.symbol_table,
        )


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


def _normalize_import_target(import_target: str) -> str:
    return import_target.strip().strip("\"'").replace("\\", "/")


def _matches_import_target(path: Path, import_target: str) -> bool:
    path_text = path.as_posix()
    target = import_target.removesuffix(".ws")

    return (
        path.name == import_target
        or path.stem == target
        or path_text.endswith(import_target)
        or path_text.removesuffix(".ws").endswith(target)
    )
