"""Completion providers."""

from lsprotocol import types

from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.parser.tokens import KEYWORDS

from .symbols import unique_symbols


def completions(index: ProjectIndex, uri: str) -> types.CompletionList:
    """Build completion items for a document.

    Args:
        index: Project index.
        uri: Current document URI.

    Returns:
        LSP completion list containing keywords and indexed symbols.
    """
    items = [_keyword_item(keyword) for keyword in sorted(KEYWORDS)]
    file_symbols = tuple(symbol for symbol in index.symbols if symbol.file_uri == uri)
    project_symbols = index.symbol_table.global_symbols()

    items.extend(
        _symbol_item(symbol) for symbol in unique_symbols((*file_symbols, *project_symbols))
    )
    return types.CompletionList(is_incomplete=False, items=items)


def _keyword_item(keyword: str) -> types.CompletionItem:
    return types.CompletionItem(
        label=keyword,
        kind=types.CompletionItemKind.Keyword,
        detail="WitcherScript keyword",
        sort_text=f"0_{keyword}",
    )


def _symbol_item(symbol: Symbol) -> types.CompletionItem:
    return types.CompletionItem(
        label=symbol.name,
        kind=_completion_kind(symbol.kind),
        detail=_symbol_detail(symbol),
        sort_text=f"1_{symbol.name}",
    )


def _completion_kind(kind: SymbolKind) -> types.CompletionItemKind:
    return {
        SymbolKind.CLASS: types.CompletionItemKind.Class,
        SymbolKind.EVENT: types.CompletionItemKind.Event,
        SymbolKind.FIELD: types.CompletionItemKind.Field,
        SymbolKind.FUNCTION: types.CompletionItemKind.Function,
        SymbolKind.LOCAL: types.CompletionItemKind.Variable,
        SymbolKind.STATE: types.CompletionItemKind.Class,
    }[kind]


def _symbol_detail(symbol: Symbol) -> str:
    if symbol.type_name is None:
        return symbol.kind.value

    return f"{symbol.kind.value}: {symbol.type_name}"
