"""Hover providers."""

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import Symbol
from witcherscript_langserver.indexing.project_index import ProjectIndex

from .lsp_utils import offset_at_position, word_at_position
from .symbols import lsp_location


def hover(
    index: ProjectIndex, source: str, uri: str, position: types.Position
) -> types.Hover | None:
    """Build hover information for a document position.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.

    Returns:
        Hover information, or ``None`` when no symbol is resolved.
    """
    word = word_at_position(source, position)
    offset = offset_at_position(source, position)

    if word is None or offset is None:
        return None

    result = NameResolver(index).resolve(uri, offset, word)

    if result is None:
        return None

    return types.Hover(
        contents=types.MarkupContent(
            kind=types.MarkupKind.Markdown,
            value=_hover_markdown(result.symbol),
        ),
        range=lsp_location(result.symbol).range,
    )


def _hover_markdown(symbol: Symbol) -> str:
    lines = [f"```witcherscript\n{_signature(symbol)}\n```"]
    lines.append(f"kind: `{symbol.kind.value}`")

    if symbol.container_name is not None:
        lines.append(f"container: `{symbol.container_name}`")

    lines.append(f"file: `{symbol.file_uri}`")
    return "\n\n".join(lines)


def _signature(symbol: Symbol) -> str:
    if symbol.type_name is None:
        return symbol.name

    return f"{symbol.name}: {symbol.type_name}"
