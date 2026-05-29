import json
from pathlib import Path
from typing import Any, cast

from witcherscript_langserver.parser.lexer import tokenize
from witcherscript_langserver.parser.tokens import KEYWORDS, TokenKind

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "tests" / "py" / "snapshots" / "lexer"


def test_valid_lexer_showcase_snapshot() -> None:
    assert _lex_snapshot("samples/scripts/valid/lexer_showcase.ws") == _load_snapshot(
        "lexer_showcase.json"
    )


def test_invalid_lexer_errors_snapshot() -> None:
    assert _lex_snapshot("samples/scripts/invalid/lexer_errors.ws") == _load_snapshot(
        "lexer_errors.json"
    )


def test_lexer_tracks_token_ranges() -> None:
    result = tokenize("class Example\n{\n}\n")
    class_token = result.tokens[0]
    left_brace = result.tokens[2]
    right_brace = result.tokens[3]
    eof = result.tokens[-1]

    assert class_token.kind == TokenKind.CLASS
    assert class_token.range.start.line == 0
    assert class_token.range.start.character == 0
    assert class_token.range.end.character == 5
    assert left_brace.range.start.line == 1
    assert left_brace.range.start.character == 0
    assert right_brace.range.start.line == 2
    assert right_brace.range.start.character == 0
    assert eof.range.start.line == 3
    assert eof.range.start.character == 0


def test_lexer_recognizes_all_configured_keywords() -> None:
    source = " ".join(KEYWORDS)
    result = tokenize(source)
    token_kinds = [token.kind for token in result.tokens[:-1]]

    assert token_kinds == list(KEYWORDS.values())
    assert result.diagnostics == []


def test_lexer_keeps_numeric_suffixes_in_number_token() -> None:
    result = tokenize("10u32 100.0f")

    assert [(token.kind, token.lexeme) for token in result.tokens] == [
        (TokenKind.NUMBER, "10u32"),
        (TokenKind.NUMBER, "100.0f"),
        (TokenKind.EOF, ""),
    ]


def _lex_snapshot(relative_path: str) -> dict[str, Any]:
    result = tokenize((ROOT / relative_path).read_text(encoding="utf-8"))
    return {
        "tokens": [
            {
                "kind": token.kind.value,
                "lexeme": token.lexeme,
            }
            for token in result.tokens
        ],
        "diagnostics": [
            {
                "code": diagnostic.code,
                "message": diagnostic.message,
            }
            for diagnostic in result.diagnostics
        ],
    }


def _load_snapshot(name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((SNAPSHOT_DIR / name).read_text(encoding="utf-8")))
