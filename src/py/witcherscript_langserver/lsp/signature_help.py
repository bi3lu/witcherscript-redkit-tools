"""Signature help provider."""

from __future__ import annotations

from dataclasses import dataclass

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import (
    CallableParameter,
    CallableSignature,
    Symbol,
    SymbolTable,
)
from witcherscript_langserver.analysis.types import TypeLookupContext, TypeLookupService
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.parser.ast import IdentifierExpr, MemberAccessExpr
from witcherscript_langserver.parser.lexer import tokenize
from witcherscript_langserver.parser.parser import ExpressionParser
from witcherscript_langserver.parser.tokens import TokenKind

from .lsp_utils import offset_at_position


@dataclass(frozen=True)
class ActiveCall:
    """Call expression detected at the cursor position.

    Attributes:
        callee_source: Source fragment before the active call opening parenthesis.
        active_parameter: Zero-based active parameter index.
    """

    callee_source: str
    active_parameter: int


def signature_help(
    index: ProjectIndex,
    source: str,
    uri: str,
    position: types.Position,
) -> types.SignatureHelp | None:
    """Build signature help for the call expression at a document position.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        position: Cursor position.

    Returns:
        LSP signature help, or ``None`` when the cursor is not inside a call.
    """
    offset = offset_at_position(source, position)

    if offset is None:
        return None

    active_call = _active_call_at_offset(source, offset)

    if active_call is None:
        return None

    resolver = NameResolver(index)
    resolution_context = resolver.context(uri, offset, "")
    lookup = TypeLookupService(index.symbol_table)
    type_context = TypeLookupContext(
        file_uri=uri,
        offset=offset,
        function_name=resolution_context.function_name,
        container_name=resolution_context.container_name,
    )
    signatures = _candidate_signatures(
        active_call.callee_source,
        index.symbol_table,
        lookup,
        type_context,
    )

    if not signatures:
        return None

    active_signature = 0
    active_parameter = _active_parameter_index(
        active_call.active_parameter,
        signatures[active_signature],
    )

    return types.SignatureHelp(
        signatures=[_signature_information(signature) for signature in signatures],
        active_signature=active_signature,
        active_parameter=active_parameter,
    )


def _active_call_at_offset(source: str, offset: int) -> ActiveCall | None:
    depth = 0
    active_parameter = 0
    index = offset - 1

    while index >= 0:
        char = source[index]

        if char == ")":
            depth += 1
            index -= 1
            continue

        if char == "(":
            if depth == 0:
                callee_source = _callee_source_before_paren(source, index)

                if callee_source is None:
                    return None

                return ActiveCall(
                    callee_source=callee_source,
                    active_parameter=active_parameter,
                )

            depth -= 1
            index -= 1
            continue

        if char == "," and depth == 0:
            active_parameter += 1

        index -= 1

    return None


def _callee_source_before_paren(source: str, paren_offset: int) -> str | None:
    prefix = source[:paren_offset].rstrip()

    if not prefix:
        return None

    start = _expression_start(prefix)
    callee_source = prefix[start:].strip()
    return callee_source or None


def _expression_start(text: str) -> int:
    depth = 0

    for index in range(len(text) - 1, -1, -1):
        char = text[index]

        if char in ")]":
            depth += 1
            continue

        if char in "([":
            if depth == 0:
                return index + 1

            depth -= 1
            continue

        if depth == 0 and char in " \t=,;{":
            return index + 1

    return 0


def _candidate_signatures(
    callee_source: str,
    symbol_table: SymbolTable,
    lookup: TypeLookupService,
    context: TypeLookupContext,
) -> tuple[CallableSignature, ...]:
    callee = _parse_callee_expression(callee_source)

    if isinstance(callee, MemberAccessExpr):
        symbol = lookup.member_symbol_for_access(callee, context)

        if symbol is None:
            return ()

        return _signatures_for_symbol(symbol, symbol_table)

    if isinstance(callee, IdentifierExpr):
        symbol = lookup.resolve_identifier(callee.name, context)

        if symbol is not None:
            signatures = _signatures_for_symbol(symbol, symbol_table)

            if signatures:
                return signatures

        return symbol_table.lookup_callable(callee.name)

    return ()


def _parse_callee_expression(callee_source: str) -> IdentifierExpr | MemberAccessExpr | None:
    result = tokenize(callee_source)
    tokens = [
        token
        for token in result.tokens
        if token.kind
        not in {
            TokenKind.BLOCK_COMMENT,
            TokenKind.EOF,
            TokenKind.LINE_COMMENT,
        }
    ]

    if not tokens:
        return None

    expression = ExpressionParser(tokens).parse()

    if isinstance(expression, IdentifierExpr | MemberAccessExpr):
        return expression

    return None


def _signatures_for_symbol(
    symbol: Symbol,
    symbol_table: SymbolTable,
) -> tuple[CallableSignature, ...]:
    return tuple(
        signature
        for signature in symbol_table.callable_signatures
        if signature.name == symbol.name
        and signature.file_uri == symbol.file_uri
        and signature.container_name == symbol.container_name
        and signature.range.start.offset == symbol.range.start.offset
    )


def _signature_information(signature: CallableSignature) -> types.SignatureInformation:
    parameters = [_parameter_label(parameter) for parameter in signature.parameters]
    label = f"{signature.name}({', '.join(parameters)})"

    if signature.return_type is not None:
        label = f"{label}: {signature.return_type}"

    return types.SignatureInformation(
        label=label,
        parameters=[
            types.ParameterInformation(label=parameter_label) for parameter_label in parameters
        ],
    )


def _parameter_label(parameter: CallableParameter) -> str:
    if parameter.type_name is None:
        return parameter.name

    return f"{parameter.name}: {parameter.type_name}"


def _active_parameter_index(active_parameter: int, signature: CallableSignature) -> int:
    if signature.parameter_count == 0:
        return 0

    return min(active_parameter, signature.parameter_count - 1)
