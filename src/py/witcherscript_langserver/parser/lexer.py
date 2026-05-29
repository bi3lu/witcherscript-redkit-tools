"""Lexer implementation for WitcherScript source files."""

from dataclasses import dataclass
from typing import ClassVar

from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.parser.tokens import (
    KEYWORDS,
    SourcePosition,
    SourceRange,
    Token,
    TokenKind,
)


@dataclass(frozen=True)
class LexResult:
    """Result of lexing a WitcherScript source file.

    Attributes:
        tokens: Tokens produced by the lexer, including the EOF token.
        diagnostics: Recoverable lexer diagnostics.
    """

    tokens: list[Token]
    diagnostics: list[SyntaxDiagnostic]


class Lexer:
    """Tokenize WitcherScript source text.

    The lexer is intentionally recoverable: malformed strings, comments, and
    unknown characters produce diagnostics while tokenization continues.
    """

    _SINGLE_CHARACTER_TOKENS: ClassVar[dict[str, TokenKind]] = {
        "(": TokenKind.LEFT_PAREN,
        ")": TokenKind.RIGHT_PAREN,
        "{": TokenKind.LEFT_BRACE,
        "}": TokenKind.RIGHT_BRACE,
        "[": TokenKind.LEFT_BRACKET,
        "]": TokenKind.RIGHT_BRACKET,
        ";": TokenKind.SEMICOLON,
        ":": TokenKind.COLON,
        ",": TokenKind.COMMA,
        ".": TokenKind.DOT,
        "?": TokenKind.QUESTION,
        "@": TokenKind.AT,
        "#": TokenKind.HASH,
        "+": TokenKind.PLUS,
        "-": TokenKind.MINUS,
        "*": TokenKind.STAR,
        "/": TokenKind.SLASH,
        "%": TokenKind.PERCENT,
        "!": TokenKind.BANG,
        "=": TokenKind.EQUAL,
        "<": TokenKind.LESS,
        ">": TokenKind.GREATER,
        "&": TokenKind.AMPERSAND,
        "|": TokenKind.PIPE,
    }

    _DOUBLE_CHARACTER_TOKENS: ClassVar[dict[str, TokenKind]] = {
        "++": TokenKind.PLUS_PLUS,
        "--": TokenKind.MINUS_MINUS,
        "+=": TokenKind.PLUS_EQUAL,
        "-=": TokenKind.MINUS_EQUAL,
        "*=": TokenKind.STAR_EQUAL,
        "/=": TokenKind.SLASH_EQUAL,
        "%=": TokenKind.PERCENT_EQUAL,
        "==": TokenKind.EQUAL_EQUAL,
        "!=": TokenKind.BANG_EQUAL,
        "<=": TokenKind.LESS_EQUAL,
        ">=": TokenKind.GREATER_EQUAL,
        "&&": TokenKind.AMPERSAND_AMPERSAND,
        "||": TokenKind.PIPE_PIPE,
        "->": TokenKind.ARROW,
        "::": TokenKind.COLON_COLON,
    }

    def __init__(self, source: str) -> None:
        """Initialize a lexer.

        Args:
            source: Full source text to tokenize.
        """
        self._source = source
        self._offset = 0
        self._line = 0
        self._character = 0
        self._tokens: list[Token] = []
        self._diagnostics: list[SyntaxDiagnostic] = []

    def tokenize(self) -> LexResult:
        """Tokenize the source text.

        Returns:
            Lexer result containing tokens and recoverable diagnostics.
        """
        while not self._is_at_end:
            self._scan_token()

        position = self._position()
        self._tokens.append(Token(TokenKind.EOF, "", SourceRange(position, position)))
        return LexResult(tokens=self._tokens, diagnostics=self._diagnostics)

    @property
    def _is_at_end(self) -> bool:
        return self._offset >= len(self._source)

    def _scan_token(self) -> None:
        self._skip_whitespace()

        if self._is_at_end:
            return

        start = self._position()
        char = self._advance()

        if _is_identifier_start(char):
            self._scan_identifier(start)
            return

        if char.isdigit():
            self._scan_number(start)
            return

        if char in {'"', "'"}:
            self._scan_string(start, char)
            return

        if char == "/" and self._match("/"):
            self._scan_line_comment(start)
            return

        if char == "/" and self._match("*"):
            self._scan_block_comment(start)
            return

        two_character = char + self._peek()

        if token_kind := self._DOUBLE_CHARACTER_TOKENS.get(two_character):
            self._advance()
            self._add_token(token_kind, start)
            return

        if token_kind := self._SINGLE_CHARACTER_TOKENS.get(char):
            self._add_token(token_kind, start)
            return

        self._add_token(TokenKind.UNKNOWN, start)
        self._diagnostics.append(
            SyntaxDiagnostic(
                code="WS1000",
                message=f"Unexpected character {char!r}.",
                range=SourceRange(start, self._position()),
            )
        )

    def _skip_whitespace(self) -> None:
        while not self._is_at_end:
            char = self._peek()

            if char in {" ", "\t", "\f", "\v"}:
                self._advance()
                continue

            if char == "\r":
                self._advance_newline()
                continue

            if char == "\n":
                self._advance_newline()
                continue

            break

    def _scan_identifier(self, start: SourcePosition) -> None:
        while _is_identifier_part(self._peek()):
            self._advance()

        lexeme = self._source[start.offset : self._offset]
        self._add_token(KEYWORDS.get(lexeme, TokenKind.IDENTIFIER), start)

    def _scan_number(self, start: SourcePosition) -> None:
        while self._peek().isdigit():
            self._advance()

        if self._peek() == "." and self._peek_next().isdigit():
            self._advance()

            while self._peek().isdigit():
                self._advance()

        if self._peek() in {"e", "E"} and (
            self._peek_next().isdigit()
            or (self._peek_next() in {"+", "-"} and self._peek_at(2).isdigit())
        ):
            self._advance()

            if self._peek() in {"+", "-"}:
                self._advance()

            while self._peek().isdigit():
                self._advance()

        if _is_identifier_start(self._peek()):
            while _is_identifier_part(self._peek()):
                self._advance()

        self._add_token(TokenKind.NUMBER, start)

    def _scan_string(self, start: SourcePosition, quote: str) -> None:
        escaped = False

        while not self._is_at_end:
            char = self._peek()

            if char in {"\n", "\r"}:
                break

            self._advance()

            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char == quote:
                self._add_token(TokenKind.STRING, start)
                return

        self._add_token(TokenKind.STRING, start)
        self._diagnostics.append(
            SyntaxDiagnostic(
                code="WS1002",
                message="Unterminated string literal.",
                range=SourceRange(start, self._position()),
            )
        )

    def _scan_line_comment(self, start: SourcePosition) -> None:
        while not self._is_at_end and self._peek() not in {"\n", "\r"}:
            self._advance()

        self._add_token(TokenKind.LINE_COMMENT, start)

    def _scan_block_comment(self, start: SourcePosition) -> None:
        while not self._is_at_end:
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                self._add_token(TokenKind.BLOCK_COMMENT, start)
                return

            if self._peek() in {"\n", "\r"}:
                self._advance_newline()

            else:
                self._advance()

        self._add_token(TokenKind.BLOCK_COMMENT, start)
        self._diagnostics.append(
            SyntaxDiagnostic(
                code="WS1003",
                message="Unterminated block comment.",
                range=SourceRange(start, self._position()),
            )
        )

    def _add_token(self, kind: TokenKind, start: SourcePosition) -> None:
        self._tokens.append(
            Token(
                kind=kind,
                lexeme=self._source[start.offset : self._offset],
                range=SourceRange(start, self._position()),
            )
        )

    def _advance(self) -> str:
        char = self._source[self._offset]
        self._offset += 1
        self._character += 1
        return char

    def _advance_newline(self) -> None:
        if self._peek() == "\r" and self._peek_next() == "\n":
            self._offset += 2

        else:
            self._offset += 1

        self._line += 1
        self._character = 0

    def _match(self, expected: str) -> bool:
        if self._peek() != expected:
            return False

        self._advance()
        return True

    def _peek(self) -> str:
        return self._peek_at(0)

    def _peek_next(self) -> str:
        return self._peek_at(1)

    def _peek_at(self, distance: int) -> str:
        offset = self._offset + distance
        if offset >= len(self._source):
            return "\0"

        return self._source[offset]

    def _position(self) -> SourcePosition:
        return SourcePosition(line=self._line, character=self._character, offset=self._offset)


def tokenize(source: str) -> LexResult:
    """Tokenize WitcherScript source text.

    Args:
        source: Full source text to tokenize.

    Returns:
        Lexer result containing tokens and recoverable diagnostics.
    """
    return Lexer(source).tokenize()


def _is_identifier_start(char: str) -> bool:
    return char == "_" or char.isalpha()


def _is_identifier_part(char: str) -> bool:
    return _is_identifier_start(char) or char.isdigit()
