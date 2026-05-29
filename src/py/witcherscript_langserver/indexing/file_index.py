"""Per-file AST and symbol index."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from witcherscript_langserver.parser.ast import (
    ClassDecl,
    Decl,
    FunctionDecl,
    Module,
    StateDecl,
    VarDecl,
)
from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.parser.parser import parse
from witcherscript_langserver.parser.tokens import SourceRange


class IndexedSymbolKind(StrEnum):
    """Kinds of symbols collected from a single WitcherScript file."""

    CLASS = "class"
    EVENT = "event"
    FUNCTION = "function"
    STATE = "state"
    VAR = "var"


@dataclass(frozen=True)
class IndexedSymbol:
    """Symbol extracted from a parsed WitcherScript file.

    Attributes:
        name: Symbol name.
        kind: Symbol kind.
        range: Source range covered by the declaration.
        container_name: Optional containing class, state, or function name.
        type_name: Declared type or return type, when available.
    """

    name: str
    kind: IndexedSymbolKind
    range: SourceRange
    container_name: str | None = None
    type_name: str | None = None


@dataclass(frozen=True)
class FileIndex:
    """Index data for one WitcherScript source file.

    Attributes:
        path: Local file path.
        uri: LSP file URI.
        module: Parsed module tree.
        symbols: Symbols extracted from the module.
        diagnostics: Recoverable lexer and parser diagnostics for the file.
    """

    path: Path
    uri: str
    module: Module
    symbols: tuple[IndexedSymbol, ...]
    diagnostics: tuple[SyntaxDiagnostic, ...]


def build_file_index(path: Path, uri: str, source: str) -> FileIndex:
    """Build an index for one WitcherScript source file.

    Args:
        path: Local file path.
        uri: LSP file URI.
        source: File source text.

    Returns:
        Parsed file index containing AST, symbols, and diagnostics.
    """
    result = parse(source)
    return FileIndex(
        path=path,
        uri=uri,
        module=result.module,
        symbols=tuple(_module_symbols(result.module)),
        diagnostics=tuple(result.diagnostics),
    )


def _module_symbols(module: Module) -> list[IndexedSymbol]:
    symbols: list[IndexedSymbol] = []

    for declaration in module.declarations:
        symbols.extend(_declaration_symbols(declaration, container_name=None))

    return symbols


def _declaration_symbols(declaration: Decl, container_name: str | None) -> list[IndexedSymbol]:
    if isinstance(declaration, ClassDecl):
        symbols = [
            IndexedSymbol(
                name=declaration.name,
                kind=IndexedSymbolKind.CLASS,
                range=declaration.range,
                container_name=container_name,
                type_name=declaration.base_name,
            )
        ]

        for member in declaration.members:
            symbols.extend(_declaration_symbols(member, container_name=declaration.name))

        return symbols

    if isinstance(declaration, StateDecl):
        symbols = [
            IndexedSymbol(
                name=declaration.name,
                kind=IndexedSymbolKind.STATE,
                range=declaration.range,
                container_name=container_name,
                type_name=declaration.parent_name,
            )
        ]

        for member in declaration.members:
            symbols.extend(_declaration_symbols(member, container_name=declaration.name))

        return symbols

    if isinstance(declaration, FunctionDecl):
        kind = (
            IndexedSymbolKind.EVENT if "event" in declaration.flags else IndexedSymbolKind.FUNCTION
        )
        symbols = [
            IndexedSymbol(
                name=declaration.name,
                kind=kind,
                range=declaration.range,
                container_name=container_name,
                type_name=declaration.return_type,
            )
        ]

        for local in declaration.locals:
            symbols.extend(_declaration_symbols(local, container_name=declaration.name))

        return symbols

    if isinstance(declaration, VarDecl):
        return [
            IndexedSymbol(
                name=declaration.name,
                kind=IndexedSymbolKind.VAR,
                range=declaration.range,
                container_name=container_name,
                type_name=declaration.type_name,
            )
        ]

    return []
