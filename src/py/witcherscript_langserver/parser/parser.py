"""Tolerant recursive-descent parser for WitcherScript source files."""

from dataclasses import dataclass

from witcherscript_langserver.parser.ast import (
    ClassDecl,
    Decl,
    FunctionDecl,
    ImportDecl,
    Module,
    ParamDecl,
    StateDecl,
    Statement,
    VarDecl,
)
from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.parser.lexer import tokenize
from witcherscript_langserver.parser.tokens import SourceRange, Token, TokenKind


@dataclass(frozen=True)
class ParseResult:
    """Result of parsing a WitcherScript source file.

    Attributes:
        module: Parsed module tree.
        diagnostics: Recoverable diagnostics gathered for this parse.
    """

    module: Module
    diagnostics: list[SyntaxDiagnostic]


FUNCTION_FLAGS = {
    TokenKind.CLEANUP,
    TokenKind.ENTRY,
    TokenKind.EXEC,
    TokenKind.FINAL,
    TokenKind.LATENT,
    TokenKind.NATIVE,
    TokenKind.PRIVATE,
    TokenKind.PROTECTED,
    TokenKind.PUBLIC,
    TokenKind.QUEST,
    TokenKind.REWARD,
    TokenKind.STORYSCENE,
    TokenKind.TIMER,
}

CLASS_FLAGS = {
    TokenKind.ABSTRACT,
    TokenKind.IMPORT,
    TokenKind.NATIVE,
    TokenKind.PRIVATE,
    TokenKind.PROTECTED,
    TokenKind.PUBLIC,
    TokenKind.STATEMACHINE,
}

PARAM_FLAGS = {TokenKind.OPTIONAL, TokenKind.OUT}
DECLARATION_STARTS = {
    TokenKind.ABSTRACT,
    TokenKind.CLASS,
    TokenKind.CLEANUP,
    TokenKind.DEFAULT,
    TokenKind.ENTRY,
    TokenKind.EVENT,
    TokenKind.EXEC,
    TokenKind.FINAL,
    TokenKind.FUNCTION,
    TokenKind.IMPORT,
    TokenKind.LATENT,
    TokenKind.NATIVE,
    TokenKind.PRIVATE,
    TokenKind.PROTECTED,
    TokenKind.PUBLIC,
    TokenKind.QUEST,
    TokenKind.REWARD,
    TokenKind.STATE,
    TokenKind.STATEMACHINE,
    TokenKind.STORYSCENE,
    TokenKind.TIMER,
    TokenKind.VAR,
}


class Parser:
    """Parse WitcherScript tokens into a tolerant structural AST.

    The parser focuses on declarations and statement boundaries first. It keeps
    enough structure for diagnostics and symbol indexing while recovering from
    incomplete code that appears during normal editing.
    """

    def __init__(self, tokens: list[Token]) -> None:
        """Initialize the parser.

        Args:
            tokens: Lexer tokens, including the EOF token.
        """
        self._tokens = [
            token
            for token in tokens
            if token.kind not in {TokenKind.LINE_COMMENT, TokenKind.BLOCK_COMMENT}
        ]
        self._current = 0
        self._diagnostics: list[SyntaxDiagnostic] = []

    def parse(self) -> ParseResult:
        """Parse a module.

        Returns:
            Parser result containing a module and recoverable diagnostics.
        """
        imports: list[ImportDecl] = []
        declarations: list[Decl] = []

        while not self._is_at_end:
            parsed = self._parse_top_level_declaration()

            if isinstance(parsed, ImportDecl):
                imports.append(parsed)

            elif parsed is not None:
                declarations.append(parsed)

            else:
                self._synchronize()

        module_range = SourceRange(self._tokens[0].range.start, self._peek().range.end)
        return ParseResult(
            module=Module(imports=imports, declarations=declarations, range=module_range),
            diagnostics=self._diagnostics,
        )

    def _parse_top_level_declaration(self) -> Decl | ImportDecl | None:
        if self._check(TokenKind.IMPORT) and self._check_next(TokenKind.STRING):
            return self._parse_import_decl()

        flags, start = self._consume_declaration_flags()

        if self._match(TokenKind.CLASS):
            return self._parse_class(flags, start)

        if self._match(TokenKind.STATE):
            return self._parse_state(self._previous())

        if self._match(TokenKind.EVENT):
            return self._parse_function([*flags, "event"], start)

        if self._match(TokenKind.FUNCTION):
            return self._parse_function(flags, start)

        if self._match(TokenKind.DEFAULT):
            return self._parse_default_var(start)

        if self._match(TokenKind.VAR):
            return self._parse_var(flags, start)

        if start is not None:
            self._error_at_current("WS2001", "Expected declaration after modifier.")
            return None

        self._error_at_current("WS1001", f"Unexpected token {self._peek().kind.value}.")
        return None

    def _parse_import_decl(self) -> ImportDecl:
        start = self._advance()
        target = self._advance()
        self._consume(TokenKind.SEMICOLON, "WS2001", "Expected ';' after import.")
        return ImportDecl(target=target.lexeme, range=self._range(start, self._previous()))

    def _parse_class(self, flags: list[str], start: Token | None) -> ClassDecl:
        start_token = start or self._previous()
        name = self._consume_name("WS2003", "Expected class name.")
        base_name = None

        if self._match(TokenKind.EXTENDS):
            base_name = self._consume_type_name("WS2004", "Expected base class name.")

        members: list[Decl] = []
        if self._match(TokenKind.LEFT_BRACE):
            while not self._check(TokenKind.RIGHT_BRACE) and not self._is_at_end:
                member = self._parse_member_declaration()

                if member is not None:
                    members.append(member)

                else:
                    self._synchronize_member()

            self._consume(TokenKind.RIGHT_BRACE, "WS2002", "Expected closing '}'.")

        else:
            self._error_at_current("WS2002", "Expected class body.")

        return ClassDecl(
            name=name,
            base_name=base_name,
            members=members,
            range=self._range(start_token, self._previous()),
            flags=flags,
        )

    def _parse_state(self, start: Token) -> StateDecl:
        name = self._consume_name("WS2003", "Expected state name.")
        parent_name = None

        if self._match(TokenKind.IN):
            parent_name = self._consume_type_name("WS2004", "Expected state parent name.")

        members: list[Decl] = []
        if self._match(TokenKind.LEFT_BRACE):
            while not self._check(TokenKind.RIGHT_BRACE) and not self._is_at_end:
                member = self._parse_member_declaration()

                if member is not None:
                    members.append(member)

                else:
                    self._synchronize_member()

            self._consume(TokenKind.RIGHT_BRACE, "WS2002", "Expected closing '}'.")

        else:
            self._error_at_current("WS2002", "Expected state body.")

        return StateDecl(
            name=name,
            parent_name=parent_name,
            members=members,
            range=self._range(start, self._previous()),
        )

    def _parse_member_declaration(self) -> Decl | None:
        flags, start = self._consume_declaration_flags()

        if self._match(TokenKind.CLASS):
            return self._parse_class(flags, start)

        if self._match(TokenKind.STATE):
            return self._parse_state(self._previous())

        if self._match(TokenKind.EVENT):
            return self._parse_function([*flags, "event"], start)

        if self._match(TokenKind.FUNCTION):
            return self._parse_function(flags, start)

        if self._match(TokenKind.DEFAULT):
            return self._parse_default_var(start)

        if self._match(TokenKind.VAR):
            return self._parse_var(flags, start)

        self._error_at_current("WS1001", f"Unexpected member token {self._peek().kind.value}.")
        return None

    def _parse_function(self, flags: list[str], start: Token | None) -> FunctionDecl:
        start_token = start or self._previous()
        name = self._consume_name("WS2005", "Expected function name.")
        params = self._parse_params()
        return_type = None

        if self._match(TokenKind.COLON):
            return_type = self._parse_type_until({TokenKind.LEFT_BRACE, TokenKind.SEMICOLON})

        body_range: SourceRange | None = None
        locals_: list[VarDecl] = []
        statements: list[Statement] = []

        if self._match(TokenKind.LEFT_BRACE):
            body_start = self._previous()
            locals_, statements = self._parse_body()
            self._consume(TokenKind.RIGHT_BRACE, "WS2002", "Expected closing '}'.")
            body_range = self._range(body_start, self._previous())

        elif self._match(TokenKind.SEMICOLON):
            body_range = None

        else:
            self._error_at_current("WS2006", "Expected function body or ';'.")

        return FunctionDecl(
            name=name,
            params=params,
            return_type=return_type,
            body_range=body_range,
            range=self._range(start_token, self._previous()),
            flags=flags,
            locals=locals_,
            statements=statements,
        )

    def _parse_params(self) -> list[ParamDecl]:
        params: list[ParamDecl] = []

        if not self._match(TokenKind.LEFT_PAREN):
            self._error_at_current("WS2007", "Expected parameter list.")
            return params

        while not self._check(TokenKind.RIGHT_PAREN) and not self._is_at_end:
            flags, start = self._consume_param_flags()
            start_token = start or self._peek()
            name = self._consume_name("WS2008", "Expected parameter name.")
            type_name = None

            if self._match(TokenKind.COLON):
                type_name = self._parse_type_until({TokenKind.COMMA, TokenKind.RIGHT_PAREN})

            else:
                self._error_at_current("WS2009", "Expected ':' after parameter name.")

            params.append(
                ParamDecl(
                    name=name,
                    type_name=type_name,
                    range=self._range(start_token, self._previous()),
                    flags=flags,
                )
            )

            if not self._match(TokenKind.COMMA):
                break

        self._consume(TokenKind.RIGHT_PAREN, "WS2010", "Expected ')' after parameters.")
        return params

    def _parse_var(self, flags: list[str], start: Token | None) -> VarDecl:
        start_token = start or self._previous()
        name = self._consume_name("WS2011", "Expected variable name.")
        type_name = None
        initializer_range = None

        if self._match(TokenKind.COLON):
            type_name = self._parse_type_until(
                DECLARATION_STARTS | {TokenKind.EQUAL, TokenKind.RIGHT_BRACE, TokenKind.SEMICOLON}
            )

        else:
            self._error_at_current("WS2012", "Expected ':' after variable name.")

        if self._match(TokenKind.EQUAL):
            initializer_start = self._peek()
            self._skip_until({TokenKind.SEMICOLON, TokenKind.RIGHT_BRACE})
            initializer_range = self._range(initializer_start, self._previous())

        self._consume(TokenKind.SEMICOLON, "WS2001", "Expected ';' after variable declaration.")
        return VarDecl(
            name=name,
            type_name=type_name,
            initializer_range=initializer_range,
            range=self._range(start_token, self._previous()),
            flags=flags,
        )

    def _parse_default_var(self, start: Token | None) -> VarDecl:
        start_token = start or self._previous()
        name = self._consume_name("WS2011", "Expected default property name.")
        initializer_range = None

        if self._match(TokenKind.EQUAL):
            initializer_start = self._peek()
            self._skip_until({TokenKind.SEMICOLON, TokenKind.RIGHT_BRACE})
            initializer_range = self._range(initializer_start, self._previous())

        else:
            self._error_at_current("WS2013", "Expected '=' after default property name.")

        self._consume(TokenKind.SEMICOLON, "WS2001", "Expected ';' after default property.")
        return VarDecl(
            name=name,
            type_name=None,
            initializer_range=initializer_range,
            range=self._range(start_token, self._previous()),
            flags=["default"],
        )

    def _parse_body(self) -> tuple[list[VarDecl], list[Statement]]:
        locals_: list[VarDecl] = []
        statements: list[Statement] = []

        while not self._check(TokenKind.RIGHT_BRACE) and not self._is_at_end:
            if self._match(TokenKind.VAR):
                var_decl = self._parse_var([], self._previous())
                locals_.append(var_decl)
                statements.append(Statement(kind="var", range=var_decl.range))
                continue

            statements.append(self._parse_statement())

        return locals_, statements

    def _parse_statement(self) -> Statement:
        start = self._peek()

        if self._match(TokenKind.LEFT_BRACE):
            self._skip_balanced_block()
            return Statement(kind="block", range=self._range(start, self._previous()))

        if self._match(TokenKind.IF):
            return self._parse_control_statement("if", start)

        if self._match(TokenKind.WHILE):
            return self._parse_control_statement("while", start)

        if self._match(TokenKind.FOR):
            return self._parse_control_statement("for", start)

        if self._match(TokenKind.SWITCH):
            return self._parse_control_statement("switch", start)

        if self._match(TokenKind.RETURN):
            expression_start = self._peek()
            self._skip_until({TokenKind.SEMICOLON, TokenKind.RIGHT_BRACE})
            expression_range = None
            if (
                not self._check_any({TokenKind.SEMICOLON, TokenKind.RIGHT_BRACE})
                or self._previous() is not start
            ):
                expression_range = self._range(expression_start, self._previous())
            self._match(TokenKind.SEMICOLON)
            return Statement(
                kind="return",
                range=self._range(start, self._previous()),
                expression_range=expression_range,
            )

        if self._match(TokenKind.BREAK):
            self._match(TokenKind.SEMICOLON)
            return Statement(kind="break", range=self._range(start, self._previous()))

        if self._match(TokenKind.CONTINUE):
            self._match(TokenKind.SEMICOLON)
            return Statement(kind="continue", range=self._range(start, self._previous()))

        self._skip_until({TokenKind.SEMICOLON, TokenKind.RIGHT_BRACE})
        self._match(TokenKind.SEMICOLON)
        return Statement(kind="expression", range=self._range(start, self._previous()))

    def _parse_control_statement(
        self,
        kind: str,
        start: Token,
    ) -> Statement:
        expression_range = self._parse_parenthesized_range()

        if self._match(TokenKind.LEFT_BRACE):
            self._skip_balanced_block()
        else:
            self._parse_statement()

        return Statement(
            kind=kind,  # type: ignore[arg-type]
            range=self._range(start, self._previous()),
            expression_range=expression_range,
        )

    def _parse_parenthesized_range(self) -> SourceRange | None:
        if not self._match(TokenKind.LEFT_PAREN):
            return None

        start = self._previous()
        depth = 1

        while depth > 0 and not self._is_at_end:
            if self._match(TokenKind.LEFT_PAREN):
                depth += 1

            elif self._match(TokenKind.RIGHT_PAREN):
                depth -= 1

            else:
                self._advance()

        return self._range(start, self._previous())

    def _parse_type_until(self, stop_kinds: set[TokenKind]) -> str | None:
        parts: list[str] = []

        while not self._check_any(stop_kinds) and not self._is_at_end:
            parts.append(self._advance().lexeme)

        type_name = " ".join(part for part in parts if part)
        return type_name or None

    def _consume_declaration_flags(self) -> tuple[list[str], Token | None]:
        flags: list[str] = []
        start: Token | None = None

        while self._check_any(FUNCTION_FLAGS | CLASS_FLAGS):
            if self._check(TokenKind.IMPORT) and self._check_next(TokenKind.STRING):
                break

            token = self._advance()
            start = start or token
            flags.append(token.lexeme)

        return flags, start

    def _consume_param_flags(self) -> tuple[list[str], Token | None]:
        flags: list[str] = []
        start: Token | None = None

        while self._check_any(PARAM_FLAGS):
            token = self._advance()
            start = start or token
            flags.append(token.lexeme)

        return flags, start

    def _consume_name(self, code: str, message: str) -> str:
        if self._check(TokenKind.IDENTIFIER) or self._check_any(
            {
                TokenKind.CLEANUP,
                TokenKind.ENTRY,
                TokenKind.QUEST,
                TokenKind.REWARD,
                TokenKind.TIMER,
            }
        ):
            return self._advance().lexeme

        self._error_at_current(code, message)
        return "<missing>"

    def _consume_type_name(self, code: str, message: str) -> str | None:
        if self._check(TokenKind.IDENTIFIER):
            return self._advance().lexeme

        self._error_at_current(code, message)
        return None

    def _skip_balanced_block(self) -> None:
        depth = 1

        while depth > 0 and not self._is_at_end:
            if self._match(TokenKind.LEFT_BRACE):
                depth += 1

            elif self._match(TokenKind.RIGHT_BRACE):
                depth -= 1

            else:
                self._advance()

    def _skip_until(self, stop_kinds: set[TokenKind]) -> None:
        depth = 0

        while not self._is_at_end:
            if depth == 0 and self._check_any(stop_kinds):
                return

            if self._match(TokenKind.LEFT_PAREN) or self._match(TokenKind.LEFT_BRACKET):
                depth += 1
                continue

            if self._match(TokenKind.RIGHT_PAREN) or self._match(TokenKind.RIGHT_BRACKET):
                depth = max(depth - 1, 0)
                continue

            self._advance()

    def _synchronize(self) -> None:
        self._advance()

        while not self._is_at_end:
            if self._previous().kind == TokenKind.SEMICOLON:
                return

            if self._check_any(DECLARATION_STARTS):
                return

            self._advance()

    def _synchronize_member(self) -> None:
        while not self._is_at_end:
            if self._check(TokenKind.RIGHT_BRACE):
                return

            if self._check_any(DECLARATION_STARTS):
                return

            self._advance()

    def _consume(self, kind: TokenKind, code: str, message: str) -> Token | None:
        if self._check(kind):
            return self._advance()

        self._error_at_current(code, message)
        return None

    def _match(self, kind: TokenKind) -> bool:
        if not self._check(kind):
            return False

        self._advance()
        return True

    def _check(self, kind: TokenKind) -> bool:
        return self._peek().kind == kind

    def _check_any(self, kinds: set[TokenKind]) -> bool:
        return self._peek().kind in kinds

    def _check_next(self, kind: TokenKind) -> bool:
        if self._current + 1 >= len(self._tokens):
            return False

        return self._tokens[self._current + 1].kind == kind

    @property
    def _is_at_end(self) -> bool:
        return self._peek().kind == TokenKind.EOF

    def _advance(self) -> Token:
        if not self._is_at_end:
            self._current += 1

        return self._previous()

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _error_at_current(self, code: str, message: str) -> None:
        token = self._peek()
        self._diagnostics.append(SyntaxDiagnostic(code=code, message=message, range=token.range))

    @staticmethod
    def _range(start: Token, end: Token) -> SourceRange:
        return SourceRange(start=start.range.start, end=end.range.end)


def parse(source: str) -> ParseResult:
    """Parse WitcherScript source text.

    Args:
        source: Full source text to lex and parse.

    Returns:
        Parser result containing the AST and recoverable diagnostics.
    """
    lex_result = tokenize(source)
    result = Parser(lex_result.tokens).parse()
    return ParseResult(
        module=result.module,
        diagnostics=[*lex_result.diagnostics, *result.diagnostics],
    )
