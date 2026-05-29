"""Symbol conversion helpers for LSP features."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from lsprotocol import types

from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind, SymbolTable
from witcherscript_langserver.diagnostics import to_lsp_range
from witcherscript_langserver.indexing.file_index import FileIndex
from witcherscript_langserver.indexing.project_index import ProjectIndex


def document_symbols(file_index: FileIndex) -> list[types.DocumentSymbol]:
    """Build document symbols for one indexed file.

    Args:
        file_index: Indexed WitcherScript file.

    Returns:
        Hierarchical LSP document symbols.
    """
    symbols_by_container: defaultdict[str | None, list[Symbol]] = defaultdict(list)

    for symbol in file_index.symbols:
        symbols_by_container[symbol.container_name].append(symbol)

    return [
        _document_symbol(symbol, symbols_by_container)
        for symbol in symbols_by_container[None]
        if _include_in_outline(symbol)
    ]


def workspace_symbols(index: ProjectIndex, query: str) -> list[types.WorkspaceSymbol]:
    """Build workspace symbol search results.

    Args:
        index: Project index.
        query: Case-insensitive query text.

    Returns:
        Matching workspace symbols.
    """
    query_lower = query.lower()
    return [
        _workspace_symbol(symbol)
        for symbol in index.symbols
        if _include_in_workspace_search(symbol) and query_lower in symbol.name.lower()
    ]


def lsp_location(symbol: Symbol) -> types.Location:
    """Convert a symbol declaration to an LSP location.

    Args:
        symbol: Indexed symbol.

    Returns:
        LSP location for the symbol declaration.
    """
    return types.Location(uri=symbol.file_uri, range=to_lsp_range(symbol.selection_range))


def find_symbol(
    table: SymbolTable, name: str, current_file_uri: str | None = None
) -> Symbol | None:
    """Find the best symbol for a name.

    Args:
        table: Project symbol table.
        name: Symbol name to resolve.
        current_file_uri: Optional file URI used to prefer local declarations.

    Returns:
        Best matching symbol, or ``None`` when unresolved.
    """
    matches = table.lookup(name)

    if not matches:
        return None

    if current_file_uri is not None:
        for symbol in matches:
            if symbol.file_uri == current_file_uri:
                return symbol

    return matches[0]


def _document_symbol(
    symbol: Symbol,
    symbols_by_container: dict[str | None, list[Symbol]],
) -> types.DocumentSymbol:
    children = [
        _document_symbol(child, symbols_by_container)
        for child in symbols_by_container.get(symbol.name, [])
        if child is not symbol and _include_in_outline(child)
    ]
    return types.DocumentSymbol(
        name=symbol.name,
        kind=_symbol_kind(symbol.kind),
        range=to_lsp_range(symbol.range),
        selection_range=to_lsp_range(symbol.selection_range),
        detail=_symbol_detail(symbol),
        children=children or None,
    )


def _workspace_symbol(symbol: Symbol) -> types.WorkspaceSymbol:
    return types.WorkspaceSymbol(
        name=symbol.name,
        kind=_symbol_kind(symbol.kind),
        location=lsp_location(symbol),
        container_name=symbol.container_name,
    )


def _symbol_kind(kind: SymbolKind) -> types.SymbolKind:
    return {
        SymbolKind.CLASS: types.SymbolKind.Class,
        SymbolKind.EVENT: types.SymbolKind.Event,
        SymbolKind.FIELD: types.SymbolKind.Field,
        SymbolKind.FUNCTION: types.SymbolKind.Function,
        SymbolKind.LOCAL: types.SymbolKind.Variable,
        SymbolKind.STATE: types.SymbolKind.Class,
    }[kind]


def _symbol_detail(symbol: Symbol) -> str | None:
    if symbol.type_name is None:
        return symbol.kind.value

    return f"{symbol.kind.value}: {symbol.type_name}"


def _include_in_outline(symbol: Symbol) -> bool:
    return symbol.kind in {
        SymbolKind.CLASS,
        SymbolKind.EVENT,
        SymbolKind.FIELD,
        SymbolKind.FUNCTION,
        SymbolKind.STATE,
    }


def _include_in_workspace_search(symbol: Symbol) -> bool:
    return symbol.kind in {
        SymbolKind.CLASS,
        SymbolKind.EVENT,
        SymbolKind.FIELD,
        SymbolKind.FUNCTION,
        SymbolKind.STATE,
    }


def unique_symbols(symbols: Iterable[Symbol]) -> tuple[Symbol, ...]:
    """Deduplicate symbols by name, kind, file, and range.

    Args:
        symbols: Symbols to deduplicate.

    Returns:
        Deduplicated symbols in input order.
    """
    seen: set[tuple[str, SymbolKind, str, int, int]] = set()
    deduplicated: list[Symbol] = []

    for symbol in symbols:
        key = (
            symbol.name,
            symbol.kind,
            symbol.file_uri,
            symbol.range.start.offset,
            symbol.range.end.offset,
        )
        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(symbol)

    return tuple(deduplicated)
