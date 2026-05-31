"""Semantic diagnostic rules."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from witcherscript_langserver.analysis.symbol_table import (
    CallableSignature,
    Symbol,
    SymbolKind,
    SymbolTable,
)
from witcherscript_langserver.analysis.types import TypeLookupContext, TypeLookupService
from witcherscript_langserver.indexing.file_index import FileIndex
from witcherscript_langserver.parser.ast import (
    ArrayAccessExpr,
    AssignmentExpr,
    BinaryExpr,
    CallExpr,
    ClassDecl,
    Decl,
    Expr,
    FunctionDecl,
    GroupingExpr,
    MemberAccessExpr,
    StateDecl,
    UnaryExpr,
    VarDecl,
)
from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.parser.lexer import tokenize
from witcherscript_langserver.parser.tokens import SourceRange, Token, TokenKind

BUILTIN_TYPES = {
    "array",
    "bool",
    "byte",
    "CName",
    "float",
    "int",
    "name",
    "string",
    "void",
}


@dataclass(frozen=True)
class SemanticDiagnosticSet:
    """Semantic diagnostics grouped by file URI.

    Attributes:
        by_file_uri: Mapping from LSP file URI to diagnostics for that file.
    """

    by_file_uri: dict[str, tuple[SyntaxDiagnostic, ...]]

    def for_file(self, file_uri: str) -> tuple[SyntaxDiagnostic, ...]:
        """Return diagnostics for one file.

        Args:
            file_uri: LSP file URI.

        Returns:
            Semantic diagnostics for the file.
        """
        return self.by_file_uri.get(file_uri, ())


def collect_semantic_diagnostics(
    files: tuple[FileIndex, ...],
    symbol_table: SymbolTable,
) -> SemanticDiagnosticSet:
    """Collect semantic diagnostics for an indexed project.

    Args:
        files: Indexed project files.
        symbol_table: Project-wide symbol table.

    Returns:
        Semantic diagnostics grouped by file URI.
    """
    diagnostics: defaultdict[str, list[SyntaxDiagnostic]] = defaultdict(list)

    for diagnostic in _duplicate_symbol_diagnostics(symbol_table):
        diagnostics[diagnostic.file_uri].append(diagnostic.to_syntax_diagnostic())

    for diagnostic in _unknown_type_diagnostics(symbol_table):
        diagnostics[diagnostic.file_uri].append(diagnostic.to_syntax_diagnostic())

    for diagnostic in _invalid_inheritance_diagnostics(symbol_table):
        diagnostics[diagnostic.file_uri].append(diagnostic.to_syntax_diagnostic())

    for diagnostic in _unresolved_import_diagnostics(files):
        diagnostics[diagnostic.file_uri].append(diagnostic.to_syntax_diagnostic())

    for file_index in files:
        diagnostics[file_index.uri].extend(_expression_diagnostics(file_index, symbol_table))

    return SemanticDiagnosticSet(
        by_file_uri={
            file_uri: tuple(_deduplicate(diagnostics_for_file))
            for file_uri, diagnostics_for_file in diagnostics.items()
        }
    )


@dataclass(frozen=True)
class _SemanticDiagnostic:
    code: str
    message: str
    range: SourceRange
    file_uri: str

    def to_syntax_diagnostic(self) -> SyntaxDiagnostic:
        """Convert the semantic diagnostic to the shared diagnostic model.

        Returns:
            Syntax-compatible diagnostic used by the LSP diagnostics pipeline.
        """
        return SyntaxDiagnostic(code=self.code, message=self.message, range=self.range)


def _duplicate_symbol_diagnostics(symbol_table: SymbolTable) -> list[_SemanticDiagnostic]:
    grouped: defaultdict[tuple[str | None, str, SymbolKind], list[Symbol]] = defaultdict(list)

    for symbol in symbol_table.symbols:
        grouped[(symbol.container_name, symbol.name, symbol.kind)].append(symbol)

    diagnostics: list[_SemanticDiagnostic] = []

    for symbols in grouped.values():
        if len(symbols) < 2:
            continue

        for duplicate in symbols[1:]:
            diagnostics.append(
                _SemanticDiagnostic(
                    code="WS3001",
                    message=f"Duplicate {duplicate.kind.value} symbol '{duplicate.name}'.",
                    range=duplicate.selection_range,
                    file_uri=duplicate.file_uri,
                )
            )

    return diagnostics


def _unknown_type_diagnostics(symbol_table: SymbolTable) -> list[_SemanticDiagnostic]:
    diagnostics: list[_SemanticDiagnostic] = []
    class_bases = {
        (symbol.file_uri, symbol.range.start.offset, symbol.type_name)
        for symbol in symbol_table.symbols
        if symbol.kind == SymbolKind.CLASS and symbol.type_name is not None
    }

    for symbol in symbol_table.symbols:
        if symbol.kind != SymbolKind.CLASS or symbol.type_name is None:
            continue

        if _is_unknown_type(symbol.type_name, symbol_table):
            diagnostics.append(
                _SemanticDiagnostic(
                    code="WS3003",
                    message=f"Base class '{symbol.type_name}' is not defined.",
                    range=symbol.range,
                    file_uri=symbol.file_uri,
                )
            )

    for reference in symbol_table.type_references:
        if (reference.file_uri, reference.range.start.offset, reference.name) in class_bases:
            continue

        if _is_unknown_type(reference.name, symbol_table):
            diagnostics.append(
                _SemanticDiagnostic(
                    code="WS3002",
                    message=f"Type '{reference.name}' is not defined.",
                    range=reference.range,
                    file_uri=reference.file_uri,
                )
            )

    return diagnostics


def _invalid_inheritance_diagnostics(symbol_table: SymbolTable) -> list[_SemanticDiagnostic]:
    diagnostics: list[_SemanticDiagnostic] = []
    class_symbols = {
        symbol.name: symbol for symbol in symbol_table.symbols if symbol.kind == SymbolKind.CLASS
    }
    state_symbols = {
        symbol.name: symbol for symbol in symbol_table.symbols if symbol.kind == SymbolKind.STATE
    }

    for symbol in class_symbols.values():
        if symbol.type_name is None:
            continue

        if symbol.type_name in state_symbols:
            diagnostics.append(
                _SemanticDiagnostic(
                    code="WS3011",
                    message=f"Class '{symbol.name}' cannot extend state '{symbol.type_name}'.",
                    range=symbol.range,
                    file_uri=symbol.file_uri,
                )
            )
            continue

        cycle = _inheritance_cycle(symbol.name, class_symbols)
        if cycle is not None:
            diagnostics.append(
                _SemanticDiagnostic(
                    code="WS3011",
                    message=f"Inheritance cycle detected: {' -> '.join(cycle)}.",
                    range=symbol.range,
                    file_uri=symbol.file_uri,
                )
            )

    return diagnostics


def _inheritance_cycle(
    class_name: str,
    class_symbols: dict[str, Symbol],
) -> tuple[str, ...] | None:
    path: list[str] = []
    current_name: str | None = class_name

    while current_name is not None:
        if current_name in path:
            cycle_start = path.index(current_name)
            return (*path[cycle_start:], current_name)

        path.append(current_name)
        current_symbol = class_symbols.get(current_name)

        if current_symbol is None:
            return None

        current_name = current_symbol.type_name

    return None


def _unresolved_import_diagnostics(files: tuple[FileIndex, ...]) -> list[_SemanticDiagnostic]:
    diagnostics: list[_SemanticDiagnostic] = []

    for file_index in files:
        for import_decl in file_index.module.imports:
            if _resolve_import(files, import_decl.target) is not None:
                continue

            diagnostics.append(
                _SemanticDiagnostic(
                    code="WS3010",
                    message=(
                        f"Import '{_display_import_target(import_decl.target)}' "
                        "could not be resolved."
                    ),
                    range=import_decl.range,
                    file_uri=file_index.uri,
                )
            )

    return diagnostics


def _resolve_import(files: tuple[FileIndex, ...], import_target: str) -> FileIndex | None:
    normalized = _display_import_target(import_target).replace("\\", "/")
    target = normalized.removesuffix(".ws")

    for file_index in files:
        path_text = file_index.path.as_posix()

        if (
            file_index.path.name == normalized
            or file_index.path.stem == target
            or path_text.endswith(normalized)
            or path_text.removesuffix(".ws").endswith(target)
        ):
            return file_index

    return None


def _display_import_target(import_target: str) -> str:
    return import_target.strip().strip("\"'")


def _expression_diagnostics(
    file_index: FileIndex,
    symbol_table: SymbolTable,
) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []
    tokens = tokenize(file_index.source).tokens

    for declaration in file_index.module.declarations:
        diagnostics.extend(
            _declaration_expression_diagnostics(
                declaration,
                symbol_table,
                tokens,
                file_uri=file_index.uri,
                container_name=None,
            )
        )

    return diagnostics


def _declaration_expression_diagnostics(
    declaration: Decl,
    symbol_table: SymbolTable,
    tokens: list[Token],
    file_uri: str,
    container_name: str | None,
) -> list[SyntaxDiagnostic]:
    if isinstance(declaration, ClassDecl | StateDecl):
        diagnostics: list[SyntaxDiagnostic] = []
        for member in declaration.members:
            diagnostics.extend(
                _declaration_expression_diagnostics(
                    member,
                    symbol_table,
                    tokens,
                    file_uri=file_uri,
                    container_name=declaration.name,
                )
            )

        return diagnostics

    if isinstance(declaration, FunctionDecl):
        return _function_expression_diagnostics(
            declaration,
            symbol_table,
            tokens,
            file_uri,
            container_name,
        )

    if isinstance(declaration, VarDecl) and declaration.initializer is not None:
        type_lookup = TypeLookupService(symbol_table)
        context = TypeLookupContext(
            file_uri=file_uri,
            offset=declaration.initializer.range.start.offset,
            function_name=None,
            container_name=container_name,
        )
        return [
            *_initializer_type_diagnostics(
                declaration.name,
                declaration.type_name,
                declaration.initializer,
                type_lookup,
                context,
            ),
            *_unknown_member_diagnostics(declaration.initializer, type_lookup, context),
            *_call_expression_diagnostics(declaration.initializer, type_lookup, context),
            *_assignment_type_diagnostics(declaration.initializer, type_lookup, context),
        ]

    return []


def _function_expression_diagnostics(
    declaration: FunctionDecl,
    symbol_table: SymbolTable,
    tokens: list[Token],
    file_uri: str,
    container_name: str | None,
) -> list[SyntaxDiagnostic]:
    known_names = _known_names(symbol_table, declaration, container_name)
    type_lookup = TypeLookupService(symbol_table)
    diagnostics: list[SyntaxDiagnostic] = []
    expression_ranges: list[SourceRange] = []
    expressions: list[Expr] = []

    for statement in declaration.statements:
        if statement.kind in {"expression", "for", "if", "return", "switch", "while"}:
            expression_ranges.append(
                statement.expression_range
                if statement.expression_range is not None
                else statement.range
            )
            if statement.expression is not None:
                expressions.append(statement.expression)
                context = TypeLookupContext(
                    file_uri=file_uri,
                    offset=statement.expression.range.start.offset,
                    function_name=declaration.name,
                    container_name=container_name,
                )
                if statement.kind == "return":
                    diagnostics.extend(
                        _return_type_diagnostics(
                            statement.expression,
                            declaration.return_type,
                            type_lookup,
                            context,
                        )
                    )

    for local in declaration.locals:
        if local.initializer_range is not None:
            expression_ranges.append(local.initializer_range)
        if local.initializer is not None:
            expressions.append(local.initializer)
            diagnostics.extend(
                _initializer_type_diagnostics(
                    local.name,
                    local.type_name,
                    local.initializer,
                    type_lookup,
                    TypeLookupContext(
                        file_uri=file_uri,
                        offset=local.initializer.range.start.offset,
                        function_name=declaration.name,
                        container_name=container_name,
                    ),
                )
            )

    for expression_range in expression_ranges:
        if expression_range is None:
            continue

        expression_tokens = _tokens_in_range(tokens, expression_range)
        diagnostics.extend(
            _unknown_identifier_diagnostics(expression_tokens, known_names, symbol_table)
        )
        diagnostics.extend(_call_diagnostics(expression_tokens, symbol_table))

    for expression in expressions:
        context = TypeLookupContext(
            file_uri=file_uri,
            offset=expression.range.start.offset,
            function_name=declaration.name,
            container_name=container_name,
        )
        diagnostics.extend(
            _unknown_member_diagnostics(
                expression,
                type_lookup,
                context,
            )
        )
        diagnostics.extend(_call_expression_diagnostics(expression, type_lookup, context))
        diagnostics.extend(_assignment_type_diagnostics(expression, type_lookup, context))

    return diagnostics


def _unknown_identifier_diagnostics(
    tokens: list[Token],
    known_names: set[str],
    symbol_table: SymbolTable,
) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []

    for index, token in enumerate(tokens):
        if token.kind != TokenKind.IDENTIFIER:
            continue

        if _next_is_left_paren(tokens, index):
            continue

        if _is_member_access(tokens, index) or _is_known_identifier(
            token.lexeme,
            known_names,
            symbol_table,
        ):
            continue

        diagnostics.append(
            SyntaxDiagnostic(
                code="WS3004",
                message=f"Identifier '{token.lexeme}' is not defined.",
                range=token.range,
            )
        )

    return diagnostics


def _call_diagnostics(tokens: list[Token], symbol_table: SymbolTable) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []

    for index, token in enumerate(tokens):
        if token.kind != TokenKind.IDENTIFIER or not _next_is_left_paren(tokens, index):
            continue

        if _is_member_access(tokens, index):
            continue

        signatures = symbol_table.lookup_callable(token.lexeme)

        if not signatures:
            diagnostics.append(
                SyntaxDiagnostic(
                    code="WS3004",
                    message=f"Function '{token.lexeme}' is not defined.",
                    range=token.range,
                )
            )
            continue

        argument_count = _argument_count(tokens, index + 1)
        if argument_count is None:
            continue

        if all(signature.parameter_count != argument_count for signature in signatures):
            expected = sorted({signature.parameter_count for signature in signatures})
            diagnostics.append(
                SyntaxDiagnostic(
                    code="WS3005",
                    message=(
                        f"Function '{token.lexeme}' expects "
                        f"{_format_expected_counts(expected)} argument(s), got {argument_count}."
                    ),
                    range=token.range,
                )
            )

    return diagnostics


def _unknown_member_diagnostics(
    expression: Expr,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []

    if isinstance(expression, MemberAccessExpr):
        target_type = type_lookup.type_of_expression(expression.target, context)

        if (
            target_type is not None
            and type_lookup.is_known_project_type(target_type)
            and type_lookup.member_for_type(target_type, expression.member) is None
        ):
            diagnostics.append(
                SyntaxDiagnostic(
                    code="WS3006",
                    message=f"Type '{target_type}' has no member '{expression.member}'.",
                    range=expression.member_range,
                )
            )

        diagnostics.extend(_unknown_member_diagnostics(expression.target, type_lookup, context))
        return diagnostics

    if isinstance(expression, CallExpr):
        diagnostics.extend(_unknown_member_diagnostics(expression.callee, type_lookup, context))
        for arg in expression.args:
            diagnostics.extend(_unknown_member_diagnostics(arg, type_lookup, context))

        return diagnostics

    if isinstance(expression, ArrayAccessExpr):
        diagnostics.extend(_unknown_member_diagnostics(expression.target, type_lookup, context))
        diagnostics.extend(_unknown_member_diagnostics(expression.index, type_lookup, context))
        return diagnostics

    if isinstance(expression, AssignmentExpr):
        diagnostics.extend(_unknown_member_diagnostics(expression.target, type_lookup, context))
        diagnostics.extend(_unknown_member_diagnostics(expression.value, type_lookup, context))
        return diagnostics

    if isinstance(expression, BinaryExpr):
        diagnostics.extend(_unknown_member_diagnostics(expression.left, type_lookup, context))
        diagnostics.extend(_unknown_member_diagnostics(expression.right, type_lookup, context))
        return diagnostics

    if isinstance(expression, GroupingExpr):
        return _unknown_member_diagnostics(expression.expression, type_lookup, context)

    if isinstance(expression, UnaryExpr):
        return _unknown_member_diagnostics(expression.operand, type_lookup, context)

    return diagnostics


def _call_expression_diagnostics(
    expression: Expr,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []

    if isinstance(expression, CallExpr):
        signature = _signature_for_call(expression, type_lookup, context)

        if signature is not None:
            diagnostics.extend(_call_argument_count_diagnostics(expression, signature))
            diagnostics.extend(
                _call_argument_type_diagnostics(expression, signature, type_lookup, context)
            )

        diagnostics.extend(_call_expression_diagnostics(expression.callee, type_lookup, context))
        for arg in expression.args:
            diagnostics.extend(_call_expression_diagnostics(arg, type_lookup, context))

        return diagnostics

    if isinstance(expression, MemberAccessExpr):
        return _call_expression_diagnostics(expression.target, type_lookup, context)

    if isinstance(expression, ArrayAccessExpr):
        diagnostics.extend(_call_expression_diagnostics(expression.target, type_lookup, context))
        diagnostics.extend(_call_expression_diagnostics(expression.index, type_lookup, context))
        return diagnostics

    if isinstance(expression, AssignmentExpr):
        diagnostics.extend(_call_expression_diagnostics(expression.target, type_lookup, context))
        diagnostics.extend(_call_expression_diagnostics(expression.value, type_lookup, context))
        return diagnostics

    if isinstance(expression, BinaryExpr):
        diagnostics.extend(_call_expression_diagnostics(expression.left, type_lookup, context))
        diagnostics.extend(_call_expression_diagnostics(expression.right, type_lookup, context))
        return diagnostics

    if isinstance(expression, GroupingExpr):
        return _call_expression_diagnostics(expression.expression, type_lookup, context)

    if isinstance(expression, UnaryExpr):
        return _call_expression_diagnostics(expression.operand, type_lookup, context)

    return diagnostics


def _signature_for_call(
    expression: CallExpr,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> CallableSignature | None:
    symbol = type_lookup.callable_symbol_for_call(expression, context)

    if symbol is None:
        return None

    for signature in type_lookup.symbol_table.callable_signatures:
        if (
            signature.name == symbol.name
            and signature.file_uri == symbol.file_uri
            and signature.container_name == symbol.container_name
            and signature.range.start.offset == symbol.range.start.offset
        ):
            return signature

    return None


def _call_argument_count_diagnostics(
    expression: CallExpr,
    signature: CallableSignature,
) -> list[SyntaxDiagnostic]:
    if len(expression.args) == signature.parameter_count:
        return []

    return [
        SyntaxDiagnostic(
            code="WS3005",
            message=(
                f"Function '{signature.name}' expects {signature.parameter_count} "
                f"argument(s), got {len(expression.args)}."
            ),
            range=expression.callee.range,
        )
    ]


def _call_argument_type_diagnostics(
    expression: CallExpr,
    signature: CallableSignature,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []

    for arg, parameter in zip(expression.args, signature.parameters, strict=False):
        actual_type = type_lookup.type_of_expression(arg, context)

        if not _types_compatible(actual_type, parameter.type_name, type_lookup):
            diagnostics.append(
                SyntaxDiagnostic(
                    code="WS3007",
                    message=(
                        f"Argument '{parameter.name}' expects type '{parameter.type_name}', "
                        f"got '{actual_type}'."
                    ),
                    range=arg.range,
                )
            )

    return diagnostics


def _assignment_type_diagnostics(
    expression: Expr,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> list[SyntaxDiagnostic]:
    diagnostics: list[SyntaxDiagnostic] = []

    if isinstance(expression, AssignmentExpr):
        target_type = type_lookup.type_of_expression(expression.target, context)
        value_type = type_lookup.type_of_expression(expression.value, context)

        if not _types_compatible(value_type, target_type, type_lookup):
            diagnostics.append(
                SyntaxDiagnostic(
                    code="WS3008",
                    message=f"Cannot assign type '{value_type}' to '{target_type}'.",
                    range=expression.value.range,
                )
            )

        diagnostics.extend(_assignment_type_diagnostics(expression.target, type_lookup, context))
        diagnostics.extend(_assignment_type_diagnostics(expression.value, type_lookup, context))
        return diagnostics

    if isinstance(expression, CallExpr):
        diagnostics.extend(_assignment_type_diagnostics(expression.callee, type_lookup, context))
        for arg in expression.args:
            diagnostics.extend(_assignment_type_diagnostics(arg, type_lookup, context))

        return diagnostics

    if isinstance(expression, MemberAccessExpr):
        return _assignment_type_diagnostics(expression.target, type_lookup, context)

    if isinstance(expression, ArrayAccessExpr):
        diagnostics.extend(_assignment_type_diagnostics(expression.target, type_lookup, context))
        diagnostics.extend(_assignment_type_diagnostics(expression.index, type_lookup, context))
        return diagnostics

    if isinstance(expression, BinaryExpr):
        diagnostics.extend(_assignment_type_diagnostics(expression.left, type_lookup, context))
        diagnostics.extend(_assignment_type_diagnostics(expression.right, type_lookup, context))
        return diagnostics

    if isinstance(expression, GroupingExpr):
        return _assignment_type_diagnostics(expression.expression, type_lookup, context)

    if isinstance(expression, UnaryExpr):
        return _assignment_type_diagnostics(expression.operand, type_lookup, context)

    return diagnostics


def _initializer_type_diagnostics(
    name: str,
    declared_type: str | None,
    initializer: Expr,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> list[SyntaxDiagnostic]:
    actual_type = type_lookup.type_of_expression(initializer, context)

    if _types_compatible(actual_type, declared_type, type_lookup):
        return []

    return [
        SyntaxDiagnostic(
            code="WS3008",
            message=(
                f"Initializer for '{name}' expects type '{declared_type}', got '{actual_type}'."
            ),
            range=initializer.range,
        )
    ]


def _return_type_diagnostics(
    expression: Expr,
    return_type: str | None,
    type_lookup: TypeLookupService,
    context: TypeLookupContext,
) -> list[SyntaxDiagnostic]:
    actual_type = type_lookup.type_of_expression(expression, context)
    expected_type = return_type or "void"

    if _types_compatible(actual_type, expected_type, type_lookup):
        return []

    return [
        SyntaxDiagnostic(
            code="WS3009",
            message=f"Return type expects '{expected_type}', got '{actual_type}'.",
            range=expression.range,
        )
    ]


def _types_compatible(
    actual_type: str | None,
    expected_type: str | None,
    type_lookup: TypeLookupService,
) -> bool:
    if actual_type is None or expected_type is None:
        return True

    actual = _normalize_type(actual_type)
    expected = _normalize_type(expected_type)

    if actual == expected:
        return True

    if actual == "int" and expected == "float":
        return True

    if actual in {"none", "null"} and expected not in BUILTIN_TYPES:
        return True

    return _is_derived_from(actual, expected, type_lookup)


def _is_derived_from(
    actual_type: str,
    expected_type: str,
    type_lookup: TypeLookupService,
) -> bool:
    current = type_lookup.resolve_type(actual_type)
    visited: set[str] = set()

    while current is not None and current.type_name is not None and current.name not in visited:
        visited.add(current.name)

        if _normalize_type(current.type_name) == expected_type:
            return True

        current = type_lookup.resolve_type(_normalize_type(current.type_name))

    return False


def _normalize_type(type_name: str) -> str:
    return " ".join(type_name.split())


def _known_names(
    symbol_table: SymbolTable,
    function: FunctionDecl,
    container_name: str | None,
) -> set[str]:
    names = {"this", *(symbol.name for symbol in symbol_table.global_symbols())}
    names.update(param.name for param in function.params)
    names.update(local.name for local in function.locals)

    if container_name is not None:
        names.update(_member_names_for_type(symbol_table, container_name))

    return names


def _member_names_for_type(symbol_table: SymbolTable, type_name: str) -> set[str]:
    names: set[str] = set()
    visited: set[str] = set()
    current_type: str | None = type_name

    while current_type is not None and current_type not in visited:
        visited.add(current_type)
        names.update(
            symbol.name
            for symbol in symbol_table.symbols
            if symbol.container_name == current_type
            and symbol.kind in {SymbolKind.FIELD, SymbolKind.FUNCTION, SymbolKind.EVENT}
        )
        current_type_symbol = symbol_table.lookup_type(current_type)
        current_type = current_type_symbol.type_name if current_type_symbol is not None else None

    return names


def _tokens_in_range(tokens: list[Token], range_: SourceRange) -> list[Token]:
    return [
        token
        for token in tokens
        if token.kind != TokenKind.EOF
        and range_.start.offset <= token.range.start.offset
        and token.range.end.offset <= range_.end.offset
    ]


def _is_unknown_type(name: str, symbol_table: SymbolTable) -> bool:
    return name not in BUILTIN_TYPES and symbol_table.lookup_type(name) is None


def _is_known_identifier(
    name: str,
    known_names: set[str],
    symbol_table: SymbolTable,
) -> bool:
    return (
        name in known_names
        or name in BUILTIN_TYPES
        or symbol_table.lookup_type(name) is not None
        or bool(symbol_table.lookup_callable(name))
    )


def _is_member_access(tokens: list[Token], index: int) -> bool:
    return index > 0 and tokens[index - 1].kind == TokenKind.DOT


def _next_is_left_paren(tokens: list[Token], index: int) -> bool:
    return index + 1 < len(tokens) and tokens[index + 1].kind == TokenKind.LEFT_PAREN


def _argument_count(tokens: list[Token], left_paren_index: int) -> int | None:
    if left_paren_index >= len(tokens) or tokens[left_paren_index].kind != TokenKind.LEFT_PAREN:
        return None

    depth = 0
    count = 0
    has_argument = False

    for token in tokens[left_paren_index:]:
        if token.kind == TokenKind.LEFT_PAREN:
            depth += 1
            if depth > 1:
                has_argument = True
            continue

        if token.kind == TokenKind.RIGHT_PAREN:
            depth -= 1
            if depth == 0:
                return count + 1 if has_argument else 0
            continue

        if depth == 1 and token.kind == TokenKind.COMMA:
            count += 1
            has_argument = False
            continue

        if depth >= 1:
            has_argument = True

    return None


def _format_expected_counts(expected: list[int]) -> str:
    if len(expected) == 1:
        return str(expected[0])

    return ", ".join(str(count) for count in expected)


def _deduplicate(diagnostics: list[SyntaxDiagnostic]) -> list[SyntaxDiagnostic]:
    seen: set[tuple[str, str, int, int]] = set()
    deduplicated: list[SyntaxDiagnostic] = []

    for diagnostic in diagnostics:
        key = (
            diagnostic.code,
            diagnostic.message,
            diagnostic.range.start.offset,
            diagnostic.range.end.offset,
        )

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(diagnostic)

    return deduplicated
