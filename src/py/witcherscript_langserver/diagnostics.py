"""Diagnostic conversion and publication helpers."""

from lsprotocol import types

DIAGNOSTIC_SOURCE = "witcherscript"


def collect_diagnostics(source: str) -> list[types.Diagnostic]:
    """Return minimal syntax diagnostics for the current LSP skeleton.

    This is intentionally small until the real lexer/parser pipeline lands. It still
    gives clients a concrete publishDiagnostics signal and catches a common broken
    edit state while typing.

    Args:
        source: Full text of the WitcherScript document being analyzed.

    Returns:
        A list of LSP diagnostics for the provided source text.
    """
    diagnostics: list[types.Diagnostic] = []
    diagnostics.extend(_diagnose_unbalanced_braces(source))

    marker_offset = source.find("syntax_error")

    if marker_offset >= 0:
        diagnostics.append(
            types.Diagnostic(
                range=_range_at_offset(source, marker_offset, len("syntax_error")),
                message="Syntax error marker found.",
                severity=types.DiagnosticSeverity.Error,
                code="WS0001",
                source=DIAGNOSTIC_SOURCE,
            )
        )

    return diagnostics


def _diagnose_unbalanced_braces(source: str) -> list[types.Diagnostic]:
    """Return diagnostics for unmatched opening or closing braces.

    Args:
        source: Full text of the WitcherScript document being analyzed.

    Returns:
        Diagnostics describing any unmatched brace characters.
    """
    diagnostics: list[types.Diagnostic] = []
    stack: list[int] = []

    for offset, char in enumerate(source):
        if char == "{":
            stack.append(offset)

        elif char == "}":
            if stack:
                stack.pop()

            else:
                diagnostics.append(
                    types.Diagnostic(
                        range=_range_at_offset(source, offset, 1),
                        message="Unexpected closing brace.",
                        severity=types.DiagnosticSeverity.Error,
                        code="WS1001",
                        source=DIAGNOSTIC_SOURCE,
                    )
                )

    for offset in stack:
        diagnostics.append(
            types.Diagnostic(
                range=_range_at_offset(source, offset, 1),
                message="Expected closing brace.",
                severity=types.DiagnosticSeverity.Error,
                code="WS2002",
                source=DIAGNOSTIC_SOURCE,
            )
        )

    return diagnostics


def _range_at_offset(source: str, offset: int, length: int) -> types.Range:
    """Create an LSP range from a source offset and character length.

    Args:
        source: Full text used for line and character calculations.
        offset: Zero-based character offset where the range starts.
        length: Number of characters covered by the range.

    Returns:
        An LSP range spanning the requested source slice.
    """
    start = _position_at_offset(source, offset)
    end = _position_at_offset(source, offset + length)
    return types.Range(start=start, end=end)


def _position_at_offset(source: str, offset: int) -> types.Position:
    """Convert a source offset to an LSP position.

    Args:
        source: Full text used for line and character calculations.
        offset: Zero-based character offset to convert.

    Returns:
        An LSP position clamped to the bounds of the source text.
    """
    safe_offset = min(max(offset, 0), len(source))
    line = source.count("\n", 0, safe_offset)
    line_start = source.rfind("\n", 0, safe_offset)
    character = safe_offset if line_start == -1 else safe_offset - line_start - 1
    return types.Position(line=line, character=character)
