"""Implementation and inheritance lookup provider."""

from __future__ import annotations

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind
from witcherscript_langserver.indexing.project_index import ProjectIndex

from .lsp_utils import offset_at_position, word_at_position
from .symbols import lsp_location


def implementations(
    index: ProjectIndex,
    source: str,
    uri: str,
    position: types.Position,
) -> list[types.Location]:
    """Return implementation locations for classes and class members.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.

    Returns:
        Locations for derived classes or override-like member declarations.
    """
    word = word_at_position(source, position)
    offset = offset_at_position(source, position)

    if word is None or offset is None:
        return []

    resolved = NameResolver(index).resolve(uri, offset, word)

    if resolved is None:
        return []

    symbol = resolved.symbol
    if symbol.kind == SymbolKind.CLASS:
        return [lsp_location(derived) for derived in _derived_class_symbols(index, symbol.name)]

    if symbol.kind in {SymbolKind.EVENT, SymbolKind.FUNCTION} and symbol.container_name is not None:
        return [
            lsp_location(candidate)
            for candidate in _override_like_symbols(index, symbol)
            if candidate != symbol
        ]

    return []


def inheritance_tree(index: ProjectIndex, class_name: str) -> dict[str, object]:
    """Build a simple inheritance tree payload for workspace commands.

    Args:
        index: Project index.
        class_name: Root class name.

    Returns:
        JSON-serializable inheritance tree.
    """
    return {
        "name": class_name,
        "base": index.inheritance_index.base_class(class_name),
        "derived": [
            inheritance_tree(index, child)
            for child in index.inheritance_index.derived_classes(class_name)
        ],
    }


def _derived_class_symbols(index: ProjectIndex, base_name: str) -> tuple[Symbol, ...]:
    symbols_by_name = {
        symbol.name: symbol for symbol in index.symbols if symbol.kind == SymbolKind.CLASS
    }
    discovered: list[Symbol] = []

    def visit(name: str) -> None:
        for child_name in index.inheritance_index.derived_classes(name):
            child = symbols_by_name.get(child_name)

            if child is None or child in discovered:
                continue

            discovered.append(child)
            visit(child.name)

    visit(base_name)
    return tuple(discovered)


def _override_like_symbols(index: ProjectIndex, symbol: Symbol) -> tuple[Symbol, ...]:
    derived_names = {
        class_symbol.name
        for class_symbol in _derived_class_symbols(index, symbol.container_name or "")
    }
    return tuple(
        candidate
        for candidate in index.symbols
        if candidate.name == symbol.name
        and candidate.kind == symbol.kind
        and candidate.container_name in derived_names
    )
