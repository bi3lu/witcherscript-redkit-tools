"""Reference providers."""

from lsprotocol import types

from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.lsp_utils import find_word_ranges, word_at_position
from witcherscript_langserver.symbols import find_symbol


def references(
    index: ProjectIndex,
    documents: dict[str, str],
    source: str,
    uri: str,
    position: types.Position,
    include_declaration: bool,
) -> list[types.Location]:
    """Find simple textual references for the symbol at a position.

    Args:
        index: Project index.
        documents: In-memory document cache keyed by URI.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.
        include_declaration: Whether the declaration location should be included.

    Returns:
        Reference locations in indexed project files.
    """
    word = word_at_position(source, position)
    if word is None:
        return []

    symbol = find_symbol(index.symbol_table, word, current_file_uri=uri)
    if symbol is None:
        return []

    locations: list[types.Location] = []

    for file_index in index.files.values():
        file_source = documents.get(file_index.uri)
        if file_source is None:
            file_source = file_index.path.read_text(encoding="utf-8")

        for range_ in find_word_ranges(file_source, symbol.name):
            if (
                not include_declaration
                and file_index.uri == symbol.file_uri
                and range_.start
                == types.Position(
                    line=symbol.selection_range.start.line,
                    character=symbol.selection_range.start.character,
                )
            ):
                continue

            locations.append(types.Location(uri=file_index.uri, range=range_))

    return locations
