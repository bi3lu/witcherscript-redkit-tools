"""Definition providers."""

from lsprotocol import types

from witcherscript_langserver.indexing.project_index import ProjectIndex

from .lsp_utils import word_at_position
from .symbols import find_symbol, lsp_location


def definition(
    index: ProjectIndex,
    source: str,
    uri: str,
    position: types.Position,
) -> types.Location | None:
    """Resolve a definition location at a document position.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.

    Returns:
        Definition location, or ``None`` when unresolved.
    """
    word = word_at_position(source, position)

    if word is None:
        return None

    symbol = find_symbol(index.symbol_table, word, current_file_uri=uri)

    if symbol is None:
        return None

    return lsp_location(symbol)
