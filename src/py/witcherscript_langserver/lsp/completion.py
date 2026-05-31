"""Completion providers."""

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind
from witcherscript_langserver.analysis.types import TypeLookupContext, TypeLookupService
from witcherscript_langserver.indexing.project_index import ProjectIndex

from .lsp_utils import offset_at_position
from .symbols import unique_symbols

TOP_LEVEL_KEYWORDS = {
    "abstract",
    "class",
    "enum",
    "final",
    "import",
    "native",
    "state",
}

MEMBER_KEYWORDS = {
    "event",
    "function",
    "private",
    "protected",
    "public",
    "state",
    "var",
}

STATEMENT_KEYWORDS = {
    "break",
    "case",
    "continue",
    "else",
    "false",
    "for",
    "if",
    "none",
    "return",
    "switch",
    "this",
    "true",
    "var",
    "while",
}


class CompletionContextKind(StrEnum):
    """Kinds of source context used to shape completion results."""

    DEFAULT = "default"
    EXTENDS = "extends"
    IMPORT = "import"
    MEMBER = "member"
    TYPE = "type"


@dataclass(frozen=True)
class CompletionContext:
    """Detected completion context.

    Attributes:
        kind: Completion context kind.
        receiver: Optional receiver expression source for member completion.
    """

    kind: CompletionContextKind
    receiver: str | None = None


def completions(
    index: ProjectIndex,
    uri: str,
    source: str = "",
    position: types.Position | None = None,
) -> types.CompletionList:
    """Build completion items for a document.

    Args:
        index: Project index.
        uri: Current document URI.
        source: Current document source text.
        position: Cursor position, when available.

    Returns:
        LSP completion list containing keywords and indexed symbols.
    """
    offset = offset_at_position(source, position) if position is not None else None
    context = _completion_context(source, offset)
    resolver = NameResolver(index)
    items = [
        _keyword_item(keyword) for keyword in _keywords_for_context(index, uri, offset, context)
    ]
    symbols = _symbols_for_context(index, resolver, uri, source, offset, context)
    imports = _import_items(index, uri) if context.kind == CompletionContextKind.IMPORT else []

    items.extend(_symbol_item(symbol) for symbol in unique_symbols(symbols))
    items.extend(imports)
    return types.CompletionList(is_incomplete=False, items=items)


def _completion_context(source: str, offset: int | None) -> CompletionContext:
    if offset is None:
        return CompletionContext(CompletionContextKind.DEFAULT)

    prefix = source[:offset]
    line_prefix = prefix[prefix.rfind("\n") + 1 :]

    if re.search(r"\bimport\s+[\"']?[^\"';]*$", line_prefix):
        return CompletionContext(CompletionContextKind.IMPORT)

    member_receiver = _member_receiver_expression(line_prefix)
    if member_receiver is not None:
        return CompletionContext(CompletionContextKind.MEMBER, receiver=member_receiver)

    if re.search(r"\bextends\s+[A-Za-z_0-9]*$", line_prefix):
        return CompletionContext(CompletionContextKind.EXTENDS)

    if _looks_like_type_context(line_prefix):
        return CompletionContext(CompletionContextKind.TYPE)

    return CompletionContext(CompletionContextKind.DEFAULT)


def _looks_like_type_context(line_prefix: str) -> bool:
    colon_index = line_prefix.rfind(":")

    if colon_index == -1:
        return False

    suffix = line_prefix[colon_index + 1 :]
    return (
        ";" not in suffix
        and "{" not in suffix
        and "}" not in suffix
        and re.fullmatch(r"\s*[A-Za-z_0-9]*", suffix) is not None
    )


def _keywords_for_context(
    index: ProjectIndex,
    uri: str,
    offset: int | None,
    context: CompletionContext,
) -> tuple[str, ...]:
    if context.kind in {
        CompletionContextKind.EXTENDS,
        CompletionContextKind.IMPORT,
        CompletionContextKind.MEMBER,
        CompletionContextKind.TYPE,
    }:
        return ()

    resolver = NameResolver(index)
    resolution_context = resolver.context(uri, offset, "") if offset is not None else None

    if resolution_context is not None and resolution_context.function_name is not None:
        return tuple(sorted(STATEMENT_KEYWORDS))

    if resolution_context is not None and resolution_context.container_name is not None:
        return tuple(sorted(MEMBER_KEYWORDS))

    return tuple(sorted(TOP_LEVEL_KEYWORDS))


def _symbols_for_context(
    index: ProjectIndex,
    resolver: NameResolver,
    uri: str,
    source: str,
    offset: int | None,
    context: CompletionContext,
) -> tuple[Symbol, ...]:
    if context.kind == CompletionContextKind.EXTENDS:
        return _type_symbols(index, kinds={SymbolKind.CLASS})

    if context.kind == CompletionContextKind.TYPE:
        return _type_symbols(index, kinds={SymbolKind.CLASS, SymbolKind.STATE})

    if context.kind == CompletionContextKind.MEMBER:
        return _member_symbols(resolver, uri, source, offset, context.receiver)

    if context.kind == CompletionContextKind.IMPORT:
        return ()

    return resolver.visible_symbols(uri, offset)


def _type_symbols(index: ProjectIndex, *, kinds: set[SymbolKind]) -> tuple[Symbol, ...]:
    return tuple(symbol for symbol in index.symbols if symbol.kind in kinds)


def _member_symbols(
    resolver: NameResolver,
    uri: str,
    source: str,
    offset: int | None,
    receiver: str | None,
) -> tuple[Symbol, ...]:
    if receiver is None or offset is None:
        return ()

    context = resolver.context(uri, offset, "")
    lookup = TypeLookupService(resolver.symbol_table)
    type_name = lookup.type_of_expression_source(
        receiver,
        TypeLookupContext(
            file_uri=uri,
            offset=offset,
            function_name=context.function_name,
            container_name=context.container_name,
        ),
    )

    if type_name is None:
        return ()

    return lookup.members_for_type(type_name)


def _member_receiver_expression(line_prefix: str) -> str | None:
    stripped = line_prefix.rstrip()
    end = len(stripped)

    while end > 0 and re.fullmatch(r"[A-Za-z_0-9]", stripped[end - 1]) is not None:
        end -= 1

    dot_index = end - 1
    if dot_index < 0 or stripped[dot_index] != ".":
        return None

    receiver_prefix = stripped[:dot_index].rstrip()
    if not receiver_prefix:
        return None

    start = _receiver_start(receiver_prefix)
    receiver = receiver_prefix[start:].strip()
    return receiver or None


def _receiver_start(text: str) -> int:
    depth = 0

    for index in range(len(text) - 1, -1, -1):
        char = text[index]

        if char in ")]":
            depth += 1
            continue

        if char in "([":
            if depth == 0:
                return index + 1

            depth -= 1
            continue

        if depth == 0 and char in " \t=,;{":
            return index + 1

    return 0


def _import_items(index: ProjectIndex, current_uri: str) -> list[types.CompletionItem]:
    items: list[types.CompletionItem] = []

    for file_index in index.files.values():
        if file_index.uri == current_uri:
            continue

        label = Path(file_index.path).with_suffix("").name
        items.append(
            types.CompletionItem(
                label=label,
                kind=types.CompletionItemKind.File,
                detail=str(file_index.path),
                sort_text=f"2_{label}",
                insert_text=f'"{label}"',
            )
        )

    return items


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
