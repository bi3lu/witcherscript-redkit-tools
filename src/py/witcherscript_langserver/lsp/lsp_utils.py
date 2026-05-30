"""Shared helpers for text-position based LSP features."""

from lsprotocol import types


def word_at_position(source: str, position: types.Position) -> str | None:
    """Return the identifier-like word at an LSP position.

    Args:
        source: Full document source text.
        position: LSP position.

    Returns:
        Identifier at the position, or ``None`` when there is no word.
    """
    offset = offset_at_position(source, position)

    if offset is None:
        return None

    if offset == len(source) and offset > 0:
        offset -= 1

    if offset < len(source) and not _is_identifier_part(source[offset]):
        if offset == 0 or not _is_identifier_part(source[offset - 1]):
            return None

        offset -= 1

    start = offset

    while start > 0 and _is_identifier_part(source[start - 1]):
        start -= 1

    end = offset

    while end < len(source) and _is_identifier_part(source[end]):
        end += 1

    if start == end:
        return None

    return source[start:end]


def offset_at_position(source: str, position: types.Position) -> int | None:
    """Convert an LSP position to a source offset.

    Args:
        source: Full document source text.
        position: LSP position.

    Returns:
        Source offset, or ``None`` when the line is outside the document.
    """
    if position.line < 0 or position.character < 0:
        return None

    line = 0
    line_start = 0

    for index, char in enumerate(source):
        if line == position.line:
            return min(line_start + position.character, _line_end(source, line_start))

        if char == "\n":
            line += 1
            line_start = index + 1

    if line == position.line:
        return min(line_start + position.character, len(source))

    return None


def find_word_ranges(source: str, word: str) -> list[types.Range]:
    """Find exact identifier occurrences in source text.

    Args:
        source: Full document source text.
        word: Identifier to find.

    Returns:
        LSP ranges for every exact word occurrence.
    """
    ranges: list[types.Range] = []
    offset = 0

    while True:
        found = source.find(word, offset)
        if found == -1:
            break

        end = found + len(word)
        before_ok = found == 0 or not _is_identifier_part(source[found - 1])
        after_ok = end == len(source) or not _is_identifier_part(source[end])

        if before_ok and after_ok:
            ranges.append(
                types.Range(
                    start=position_at_offset(source, found),
                    end=position_at_offset(source, end),
                )
            )

        offset = end

    return ranges


def position_at_offset(source: str, offset: int) -> types.Position:
    """Convert a source offset to an LSP position.

    Args:
        source: Full document source text.
        offset: Source offset.

    Returns:
        LSP position clamped to the source bounds.
    """
    safe_offset = min(max(offset, 0), len(source))
    line = source.count("\n", 0, safe_offset)
    line_start = source.rfind("\n", 0, safe_offset)
    character = safe_offset if line_start == -1 else safe_offset - line_start - 1
    return types.Position(line=line, character=character)


def _line_end(source: str, line_start: int) -> int:
    newline = source.find("\n", line_start)

    if newline == -1:
        return len(source)

    return newline


def _is_identifier_part(char: str) -> bool:
    return char == "_" or char.isalpha() or char.isdigit()
