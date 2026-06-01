"""Rename provider with conservative local-symbol edits."""

from __future__ import annotations

import re

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import Scope, ScopeKind, Symbol, SymbolKind
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.parser.tokens import SourceRange

from .lsp_utils import (
    find_word_ranges,
    offset_at_position,
    word_at_position,
    word_range_at_position,
)

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")


def prepare_rename(
    index: ProjectIndex,
    source: str,
    uri: str,
    position: types.Position,
) -> types.Range | None:
    """Return the range that can be safely renamed.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.

    Returns:
        Rename range for local symbols, or ``None`` when unsupported.
    """
    if _renamable_local_symbol(index, source, uri, position) is None:
        return None

    return word_range_at_position(source, position)


def rename_symbol(
    index: ProjectIndex,
    source: str,
    uri: str,
    position: types.Position,
    new_name: str,
) -> types.WorkspaceEdit | None:
    """Rename a local variable or parameter within its function scope.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.
        new_name: Requested replacement identifier.

    Returns:
        Workspace edit for a safe local rename, or ``None`` when unsupported.
    """
    if IDENTIFIER_PATTERN.fullmatch(new_name) is None:
        return None

    symbol = _renamable_local_symbol(index, source, uri, position)
    offset = offset_at_position(source, position)

    if symbol is None or offset is None:
        return None

    function_scope = _function_scope(index, uri, offset, symbol.container_name)

    if function_scope is None:
        return None

    edits = [
        types.TextEdit(range=range_, new_text=new_name)
        for range_ in find_word_ranges(source, symbol.name)
        if _range_inside_scope(source, range_, function_scope.range)
    ]

    if not edits:
        return None

    return types.WorkspaceEdit(changes={uri: edits})


def _renamable_local_symbol(
    index: ProjectIndex,
    source: str,
    uri: str,
    position: types.Position,
) -> Symbol | None:
    word = word_at_position(source, position)
    offset = offset_at_position(source, position)

    if word is None or offset is None:
        return None

    result = NameResolver(index).resolve(uri, offset, word)

    if result is None or result.symbol.kind != SymbolKind.LOCAL:
        return None

    return result.symbol


def _function_scope(
    index: ProjectIndex,
    uri: str,
    offset: int,
    function_name: str | None,
) -> Scope | None:
    scopes = [
        scope
        for scope in index.scopes
        if scope.file_uri == uri
        and scope.kind == ScopeKind.FUNCTION
        and scope.name == function_name
        and _contains_offset(scope.range, offset)
    ]
    return min(
        scopes,
        key=lambda scope: scope.range.end.offset - scope.range.start.offset,
        default=None,
    )


def _range_inside_scope(source: str, range_: types.Range, scope_range: SourceRange) -> bool:
    start = offset_at_position(source, range_.start)
    end = offset_at_position(source, range_.end)

    if start is None or end is None:
        return False

    return scope_range.start.offset <= start and end <= scope_range.end.offset


def _contains_offset(range_: SourceRange, offset: int) -> bool:
    return range_.start.offset <= offset <= range_.end.offset
