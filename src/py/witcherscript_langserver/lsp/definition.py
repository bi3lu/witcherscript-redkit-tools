"""Definition providers."""

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.indexing.project_index import ProjectIndex

from .lsp_utils import offset_at_position, word_at_position
from .symbols import lsp_location


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
    offset = offset_at_position(source, position)

    if word is None or offset is None:
        return None

    result = NameResolver(index).resolve(uri, offset, word)

    if result is None:
        return None

    return lsp_location(result.symbol)
