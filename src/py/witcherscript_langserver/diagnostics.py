"""Diagnostic conversion helpers for LSP publication."""

from lsprotocol import types

from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.parser.parser import parse
from witcherscript_langserver.parser.tokens import SourcePosition, SourceRange

DIAGNOSTIC_SOURCE = "witcherscript"


def collect_diagnostics(source: str) -> list[types.Diagnostic]:
    """Return syntax diagnostics produced by the lexer and parser.

    Args:
        source: Full text of the WitcherScript document being analyzed.

    Returns:
        Deduplicated LSP diagnostics for the provided source text.
    """
    return _deduplicate(
        [_to_lsp_diagnostic(diagnostic) for diagnostic in parse(source).diagnostics]
    )


def _to_lsp_diagnostic(diagnostic: SyntaxDiagnostic) -> types.Diagnostic:
    """Convert a lexer or parser diagnostic to an LSP diagnostic.

    Args:
        diagnostic: Internal syntax diagnostic.

    Returns:
        LSP diagnostic suitable for ``textDocument/publishDiagnostics``.
    """
    return types.Diagnostic(
        range=to_lsp_range(diagnostic.range),
        message=diagnostic.message,
        severity=types.DiagnosticSeverity.Error,
        code=diagnostic.code,
        source=DIAGNOSTIC_SOURCE,
    )


def to_lsp_range(source_range: SourceRange) -> types.Range:
    """Convert a WitcherScript source range to an LSP range.

    Args:
        source_range: Parser source range using zero-based line and column positions.

    Returns:
        Equivalent LSP range.
    """
    return types.Range(
        start=_to_lsp_position(source_range.start),
        end=_to_lsp_position(source_range.end),
    )


def _to_lsp_position(position: SourcePosition) -> types.Position:
    return types.Position(line=position.line, character=position.character)


def _deduplicate(diagnostics: list[types.Diagnostic]) -> list[types.Diagnostic]:
    seen: set[tuple[str | int | None, str, int, int, int, int]] = set()
    deduplicated: list[types.Diagnostic] = []

    for diagnostic in diagnostics:
        key = (
            diagnostic.code,
            diagnostic.message,
            diagnostic.range.start.line,
            diagnostic.range.start.character,
            diagnostic.range.end.line,
            diagnostic.range.end.character,
        )

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(diagnostic)

    return deduplicated
