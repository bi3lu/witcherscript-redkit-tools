"""Type lookup services for WitcherScript expressions and symbols."""

from __future__ import annotations

import re
from dataclasses import dataclass

from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind, SymbolTable
from witcherscript_langserver.parser.ast import (
    ArrayAccessExpr,
    AssignmentExpr,
    BinaryExpr,
    CallExpr,
    Expr,
    GroupingExpr,
    IdentifierExpr,
    LiteralExpr,
    MemberAccessExpr,
    UnaryExpr,
)
from witcherscript_langserver.parser.lexer import tokenize
from witcherscript_langserver.parser.parser import ExpressionParser
from witcherscript_langserver.parser.tokens import TokenKind

BUILTIN_TYPES = {
    "array",
    "bool",
    "byte",
    "CName",
    "float",
    "int",
    "name",
    "none",
    "string",
    "void",
}


@dataclass(frozen=True)
class TypeLookupContext:
    """Source context used for expression type lookup.

    Attributes:
        file_uri: LSP file URI where lookup is requested.
        offset: Source offset where lookup is requested.
        function_name: Current function or event name, when inside one.
        container_name: Current class or state name, when inside one.
    """

    file_uri: str
    offset: int
    function_name: str | None
    container_name: str | None


class TypeLookupService:
    """Resolve expression types and class members from the symbol table."""

    def __init__(self, symbol_table: SymbolTable) -> None:
        """Initialize the type lookup service.

        Args:
            symbol_table: Project-wide symbols used for type and member lookup.
        """
        self._symbol_table = symbol_table

    def type_of_expression_source(
        self,
        expression_source: str,
        context: TypeLookupContext,
    ) -> str | None:
        """Resolve the type of a source fragment containing one expression.

        Args:
            expression_source: Source text for the expression to parse.
            context: Source context used for identifier lookup.

        Returns:
            Resolved type name, or ``None`` when it cannot be inferred.
        """
        expression = _parse_expression_source(expression_source)

        if expression is None:
            return None

        return self.type_of_expression(expression, context)

    def type_of_expression(self, expression: Expr, context: TypeLookupContext) -> str | None:
        """Resolve the type of an expression AST node.

        Args:
            expression: Expression node to inspect.
            context: Source context used for identifier lookup.

        Returns:
            Resolved type name, or ``None`` when it cannot be inferred.
        """
        if isinstance(expression, LiteralExpr):
            return _literal_type(expression)

        if isinstance(expression, IdentifierExpr):
            return self._type_of_identifier(expression.name, context)

        if isinstance(expression, GroupingExpr | UnaryExpr):
            return (
                self.type_of_expression(expression.expression, context)
                if isinstance(expression, GroupingExpr)
                else self.type_of_expression(expression.operand, context)
            )

        if isinstance(expression, BinaryExpr):
            return self._type_of_binary_expression(expression, context)

        if isinstance(expression, AssignmentExpr):
            return self.type_of_expression(expression.value, context)

        if isinstance(expression, ArrayAccessExpr):
            target_type = self.type_of_expression(expression.target, context)
            return _array_element_type(target_type)

        if isinstance(expression, MemberAccessExpr):
            symbol = self.member_symbol_for_access(expression, context)
            return _type_of_symbol(symbol) if symbol is not None else None

        if isinstance(expression, CallExpr):
            symbol = self.callable_symbol_for_call(expression, context)

            if symbol is not None:
                return _type_of_symbol(symbol)

            if isinstance(expression.callee, IdentifierExpr):
                type_symbol = self.resolve_type(expression.callee.name)
                return type_symbol.name if type_symbol is not None else None

        return None

    def member_symbol_for_access(
        self,
        expression: MemberAccessExpr,
        context: TypeLookupContext,
    ) -> Symbol | None:
        """Resolve the symbol referenced by a member access expression.

        Args:
            expression: Member access expression.
            context: Source context used for receiver type lookup.

        Returns:
            Matching member symbol, or ``None`` when unresolved.
        """
        target_type = self.type_of_expression(expression.target, context)

        if target_type is None:
            return None

        return self.member_for_type(target_type, expression.member)

    def callable_symbol_for_call(
        self,
        expression: CallExpr,
        context: TypeLookupContext,
    ) -> Symbol | None:
        """Resolve the callable symbol used by a call expression.

        Args:
            expression: Call expression.
            context: Source context used for receiver or identifier lookup.

        Returns:
            Matching function or event symbol, or ``None`` when unresolved.
        """
        if isinstance(expression.callee, MemberAccessExpr):
            symbol = self.member_symbol_for_access(expression.callee, context)

            if symbol is not None and symbol.kind in {SymbolKind.EVENT, SymbolKind.FUNCTION}:
                return symbol

            return None

        if isinstance(expression.callee, IdentifierExpr):
            symbol = self.resolve_identifier(expression.callee.name, context)

            if symbol is not None and symbol.kind in {SymbolKind.EVENT, SymbolKind.FUNCTION}:
                return symbol

        return None

    def resolve_identifier(self, name: str, context: TypeLookupContext) -> Symbol | None:
        """Resolve an identifier-like name in a source context.

        Args:
            name: Name to resolve.
            context: Current source context.

        Returns:
            Matching symbol, or ``None`` when unresolved.
        """
        if context.function_name is not None:
            local = self._lookup_local(context.file_uri, context.function_name, name)

            if local is not None:
                return local

        if context.container_name is not None:
            member = self.member_for_type(context.container_name, name)

            if member is not None:
                return member

        for symbol in self._symbol_table.global_symbols():
            if symbol.name == name:
                return symbol

        return self.resolve_type(name)

    def resolve_type(self, name: str) -> Symbol | None:
        """Resolve a class or state type by name.

        Args:
            name: Type name.

        Returns:
            Matching class or state symbol, or ``None`` when unresolved.
        """
        return self._symbol_table.lookup_type(name)

    def member_for_type(self, type_name: str, member_name: str) -> Symbol | None:
        """Resolve a member declared on a type or inherited from a base type.

        Args:
            type_name: Receiver type name.
            member_name: Member name to find.

        Returns:
            Matching member symbol, or ``None`` when unresolved.
        """
        for member in self.members_for_type(type_name):
            if member.name == member_name:
                return member

        return None

    def members_for_type(self, type_name: str) -> tuple[Symbol, ...]:
        """Return fields, methods, and events visible on a type.

        Args:
            type_name: Class or state type name.

        Returns:
            Members declared on the type followed by inherited members.
        """
        members: list[Symbol] = []
        visited: set[str] = set()
        current_type = _primary_type_name(type_name)

        while current_type is not None and current_type not in visited:
            visited.add(current_type)
            members.extend(
                symbol
                for symbol in self._symbol_table.symbols
                if symbol.container_name == current_type
                and symbol.kind in {SymbolKind.EVENT, SymbolKind.FIELD, SymbolKind.FUNCTION}
            )
            current_type_symbol = self.resolve_type(current_type)
            current_type = (
                current_type_symbol.type_name if current_type_symbol is not None else None
            )

        return tuple(_deduplicate_members(members))

    def is_known_project_type(self, type_name: str) -> bool:
        """Return whether a type name resolves to an indexed project type.

        Args:
            type_name: Type name to check.

        Returns:
            ``True`` when the type is a known class or state.
        """
        primary = _primary_type_name(type_name)
        return primary is not None and self.resolve_type(primary) is not None

    @property
    def symbol_table(self) -> SymbolTable:
        """Return the symbol table backing this lookup service.

        Returns:
            Project-wide symbol table.
        """
        return self._symbol_table

    def _type_of_identifier(self, name: str, context: TypeLookupContext) -> str | None:
        if name == "this":
            return context.container_name

        if name in {"parent", "super"} and context.container_name is not None:
            container_symbol = self.resolve_type(context.container_name)
            return container_symbol.type_name if container_symbol is not None else None

        symbol = self.resolve_identifier(name, context)
        return _type_of_symbol(symbol) if symbol is not None else None

    def _lookup_local(
        self,
        file_uri: str,
        function_name: str,
        name: str,
    ) -> Symbol | None:
        matches = [
            symbol
            for symbol in self._symbol_table.symbols
            if symbol.file_uri == file_uri
            and symbol.container_name == function_name
            and symbol.name == name
            and symbol.kind == SymbolKind.LOCAL
        ]
        return matches[-1] if matches else None

    def _type_of_binary_expression(
        self,
        expression: BinaryExpr,
        context: TypeLookupContext,
    ) -> str | None:
        if expression.operator in {"&&", "||", "==", "!=", "<", "<=", ">", ">="}:
            return "bool"

        left_type = self.type_of_expression(expression.left, context)
        right_type = self.type_of_expression(expression.right, context)

        if "float" in {left_type, right_type}:
            return "float"

        return left_type or right_type


def _parse_expression_source(source: str) -> Expr | None:
    result = tokenize(source)
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

    return ExpressionParser(tokens).parse()


def _literal_type(expression: LiteralExpr) -> str:
    if expression.literal_kind == "number":
        return "float" if _looks_like_float(expression.value) else "int"

    return expression.literal_kind


def _looks_like_float(value: str) -> bool:
    return "." in value or "e" in value.lower() or value.lower().endswith("f")


def _array_element_type(type_name: str | None) -> str | None:
    if type_name is None:
        return None

    match = re.fullmatch(r"\s*array\s*<\s*(?P<item>[^>]+?)\s*>\s*", type_name)

    if match is None:
        return None

    return match.group("item").strip()


def _type_of_symbol(symbol: Symbol | None) -> str | None:
    if symbol is None:
        return None

    if symbol.kind in {SymbolKind.CLASS, SymbolKind.STATE}:
        return symbol.name

    return symbol.type_name


def _primary_type_name(type_name: str | None) -> str | None:
    if type_name is None:
        return None

    match = re.search(r"[A-Za-z_][A-Za-z0-9_]*", type_name)
    return match.group(0) if match is not None else None


def _deduplicate_members(symbols: list[Symbol]) -> list[Symbol]:
    seen: set[str] = set()
    deduplicated: list[Symbol] = []

    for symbol in symbols:
        if symbol.name in seen:
            continue

        seen.add(symbol.name)
        deduplicated.append(symbol)

    return deduplicated
