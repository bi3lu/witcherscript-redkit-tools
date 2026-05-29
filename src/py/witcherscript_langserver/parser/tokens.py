"""Token models."""

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, order=True)
class SourcePosition:
    """A zero-based source position.

    Attributes:
        line: Zero-based source line.
        character: Zero-based character within the source line.
        offset: Zero-based character offset from the beginning of the source.
    """

    line: int
    character: int
    offset: int


@dataclass(frozen=True)
class SourceRange:
    """A half-open source range.

    Attributes:
        start: Inclusive start position.
        end: Exclusive end position.
    """

    start: SourcePosition
    end: SourcePosition


class TokenKind(StrEnum):
    """Kinds of tokens produced by the WitcherScript lexer."""

    EOF = "EOF"
    UNKNOWN = "UNKNOWN"

    IDENTIFIER = "IDENTIFIER"
    NUMBER = "NUMBER"
    STRING = "STRING"
    LINE_COMMENT = "LINE_COMMENT"
    BLOCK_COMMENT = "BLOCK_COMMENT"

    CLASS = "CLASS"
    EXTENDS = "EXTENDS"
    STATE = "STATE"
    FUNCTION = "FUNCTION"
    EVENT = "EVENT"
    VAR = "VAR"
    DEFAULT = "DEFAULT"
    IMPORT = "IMPORT"
    RETURN = "RETURN"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    FOR = "FOR"
    SWITCH = "SWITCH"
    CASE = "CASE"
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"
    TRUE = "TRUE"
    FALSE = "FALSE"
    NONE = "NONE"

    LEFT_PAREN = "LEFT_PAREN"
    RIGHT_PAREN = "RIGHT_PAREN"
    LEFT_BRACE = "LEFT_BRACE"
    RIGHT_BRACE = "RIGHT_BRACE"
    LEFT_BRACKET = "LEFT_BRACKET"
    RIGHT_BRACKET = "RIGHT_BRACKET"
    SEMICOLON = "SEMICOLON"
    COLON = "COLON"
    COMMA = "COMMA"
    DOT = "DOT"
    QUESTION = "QUESTION"
    AT = "AT"
    HASH = "HASH"

    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    PERCENT = "PERCENT"
    BANG = "BANG"
    EQUAL = "EQUAL"
    LESS = "LESS"
    GREATER = "GREATER"
    AMPERSAND = "AMPERSAND"
    PIPE = "PIPE"

    PLUS_PLUS = "PLUS_PLUS"
    MINUS_MINUS = "MINUS_MINUS"
    PLUS_EQUAL = "PLUS_EQUAL"
    MINUS_EQUAL = "MINUS_EQUAL"
    STAR_EQUAL = "STAR_EQUAL"
    SLASH_EQUAL = "SLASH_EQUAL"
    PERCENT_EQUAL = "PERCENT_EQUAL"
    EQUAL_EQUAL = "EQUAL_EQUAL"
    BANG_EQUAL = "BANG_EQUAL"
    LESS_EQUAL = "LESS_EQUAL"
    GREATER_EQUAL = "GREATER_EQUAL"
    AMPERSAND_AMPERSAND = "AMPERSAND_AMPERSAND"
    PIPE_PIPE = "PIPE_PIPE"
    ARROW = "ARROW"
    COLON_COLON = "COLON_COLON"


KEYWORDS: dict[str, TokenKind] = {
    "class": TokenKind.CLASS,
    "extends": TokenKind.EXTENDS,
    "state": TokenKind.STATE,
    "function": TokenKind.FUNCTION,
    "event": TokenKind.EVENT,
    "var": TokenKind.VAR,
    "default": TokenKind.DEFAULT,
    "import": TokenKind.IMPORT,
    "return": TokenKind.RETURN,
    "if": TokenKind.IF,
    "else": TokenKind.ELSE,
    "while": TokenKind.WHILE,
    "for": TokenKind.FOR,
    "switch": TokenKind.SWITCH,
    "case": TokenKind.CASE,
    "break": TokenKind.BREAK,
    "continue": TokenKind.CONTINUE,
    "true": TokenKind.TRUE,
    "false": TokenKind.FALSE,
    "none": TokenKind.NONE,
}


@dataclass(frozen=True)
class Token:
    """A token emitted by the lexer.

    Attributes:
        kind: Token kind.
        lexeme: Original source text covered by the token.
        range: Source range covered by the token.
    """

    kind: TokenKind
    lexeme: str
    range: SourceRange
