"""Parser and lexer errors."""

from dataclasses import dataclass

from witcherscript_langserver.parser.tokens import SourceRange


@dataclass(frozen=True)
class SyntaxDiagnostic:
    """Diagnostic produced while lexing or parsing WitcherScript.

    Attributes:
        code: Stable diagnostic code.
        message: Human-readable diagnostic message.
        range: Source range where the diagnostic should be reported.
    """

    code: str
    message: str
    range: SourceRange
