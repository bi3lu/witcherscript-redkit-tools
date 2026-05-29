from lsprotocol import types

from witcherscript_langserver.diagnostics import _deduplicate, collect_diagnostics


def test_collects_lexer_diagnostics() -> None:
    diagnostics = collect_diagnostics('class Broken {\n var title : string = "oops\n}')

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS1002", "Unterminated string literal."),
        ("WS2001", "Expected ';' after variable declaration."),
    ]
    assert diagnostics[0].range.start.line == 1
    assert diagnostics[0].range.start.character == 22
    assert diagnostics[0].range.end.line == 1
    assert diagnostics[0].range.end.character == 27
    assert all(diagnostic.severity == types.DiagnosticSeverity.Error for diagnostic in diagnostics)
    assert all(diagnostic.source == "witcherscript" for diagnostic in diagnostics)


def test_collects_parser_diagnostics() -> None:
    diagnostics = collect_diagnostics("class Broken { var value : int function ok() {} }")

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS2001", "Expected ';' after variable declaration.")
    ]
    assert diagnostics[0].range.start.line == 0
    assert diagnostics[0].range.start.character == 31
    assert diagnostics[0].range.end.line == 0
    assert diagnostics[0].range.end.character == 39


def test_collects_missing_closing_brace_diagnostic() -> None:
    diagnostics = collect_diagnostics("class Player {")

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS2002", "Expected closing '}'.")
    ]
    assert diagnostics[0].range.start.line == 0
    assert diagnostics[0].range.start.character == 14
    assert diagnostics[0].range.end.line == 0
    assert diagnostics[0].range.end.character == 14


def test_collects_unexpected_token_diagnostic() -> None:
    diagnostics = collect_diagnostics("class Broken {\n $\n}")

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS1000", "Unexpected character '$'."),
        ("WS1001", "Unexpected member token UNKNOWN."),
    ]
    assert diagnostics[0].range.start.line == 1
    assert diagnostics[0].range.start.character == 1
    assert diagnostics[0].range.end.line == 1
    assert diagnostics[0].range.end.character == 2


def test_collects_unexpected_keyword_diagnostic() -> None:
    diagnostics = collect_diagnostics("else")

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS1001", "Unexpected token ELSE.")
    ]
    assert diagnostics[0].range.start.line == 0
    assert diagnostics[0].range.start.character == 0
    assert diagnostics[0].range.end.line == 0
    assert diagnostics[0].range.end.character == 4


def test_deduplicates_identical_diagnostics() -> None:
    diagnostic = types.Diagnostic(
        range=types.Range(
            start=types.Position(line=1, character=2),
            end=types.Position(line=1, character=3),
        ),
        message="Expected ';' after variable declaration.",
        severity=types.DiagnosticSeverity.Error,
        code="WS2001",
        source="witcherscript",
    )

    assert _deduplicate([diagnostic, diagnostic]) == [diagnostic]
