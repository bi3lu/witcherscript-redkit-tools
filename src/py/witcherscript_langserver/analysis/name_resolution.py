"""Context-aware name resolution for WitcherScript symbols."""

from __future__ import annotations

from dataclasses import dataclass

from witcherscript_langserver.analysis.symbol_table import (
    Scope,
    ScopeKind,
    Symbol,
    SymbolKind,
    SymbolTable,
)
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.parser.tokens import SourceRange


@dataclass(frozen=True)
class ResolutionContext:
    """Source context used for resolving a name.

    Attributes:
        file_uri: LSP file URI where resolution is requested.
        offset: Source offset where resolution is requested.
        word: Identifier-like word under the cursor.
        scope: Innermost structural scope at the requested offset.
        function_name: Current function or event scope name.
        container_name: Current class or state scope name.
    """

    file_uri: str
    offset: int
    word: str
    scope: Scope | None
    function_name: str | None
    container_name: str | None


@dataclass(frozen=True)
class ResolutionResult:
    """Resolved symbol and the scope category that produced it.

    Attributes:
        symbol: Symbol selected by name resolution.
        source: Resolution category, such as ``local`` or ``inherited_member``.
    """

    symbol: Symbol
    source: str


class NameResolver:
    """Resolve names against locals, members, inheritance, and globals."""

    def __init__(self, index: ProjectIndex) -> None:
        """Initialize a resolver for a project index.

        Args:
            index: Project index used for symbol lookup.
        """
        self._index = index

    def resolve(self, file_uri: str, offset: int, word: str) -> ResolutionResult | None:
        """Resolve a word at a source offset.

        Args:
            file_uri: LSP file URI where resolution is requested.
            offset: Source offset where resolution is requested.
            word: Identifier-like word under the cursor.

        Returns:
            Resolution result, or ``None`` when the name is unknown.
        """
        context = self.context(file_uri, offset, word)

        if word == "this" and context.container_name is not None:
            class_symbol = self.resolve_type(context.container_name)

            if class_symbol is not None:
                return ResolutionResult(class_symbol, "this")

        if context.function_name is not None:
            local = self._lookup_local(context.file_uri, context.function_name, context.word)

            if local is not None:
                return ResolutionResult(local, "local")

        if context.container_name is not None:
            member = self._lookup_member(context.container_name, context.word)

            if member is not None:
                source = (
                    "member"
                    if member.container_name == context.container_name
                    else "inherited_member"
                )
                return ResolutionResult(member, source)

        global_symbol = self._lookup_global(context.word, context.file_uri)
        if global_symbol is not None:
            return ResolutionResult(global_symbol, "global")

        type_symbol = self.resolve_type(context.word)
        if type_symbol is not None:
            return ResolutionResult(type_symbol, "type")

        return None

    def visible_symbols(self, file_uri: str, offset: int | None = None) -> tuple[Symbol, ...]:
        """Return symbols visible from a file and optional offset.

        Args:
            file_uri: LSP file URI for the current document.
            offset: Optional source offset used to include locals and members.

        Returns:
            Visible symbols ordered from most specific to broadest scope.
        """
        context = self.context(file_uri, offset, "") if offset is not None else None
        symbols: list[Symbol] = []

        if context is not None and context.function_name is not None:
            symbols.extend(self._locals_in_function(file_uri, context.function_name))

        if context is not None and context.container_name is not None:
            symbols.extend(self._members_for_type(context.container_name))

        symbols.extend(self._index.symbol_table.global_symbols())
        return tuple(_deduplicate_symbols(symbols))

    def members_for_type(self, type_name: str) -> tuple[Symbol, ...]:
        """Return members declared on a type and its base classes.

        Args:
            type_name: Class or state type name.

        Returns:
            Fields, functions, and events visible on the type.
        """
        return self._members_for_type(type_name)

    @property
    def symbol_table(self) -> SymbolTable:
        """Return the project symbol table used by this resolver.

        Returns:
            Project-wide symbol table.
        """
        return self._index.symbol_table

    def resolve_type(self, name: str) -> Symbol | None:
        """Resolve a class or state type by name.

        Args:
            name: Type-like symbol name.

        Returns:
            Matching class or state symbol, when known.
        """
        return self._index.symbol_table.lookup_type(name)

    def context(self, file_uri: str, offset: int, word: str) -> ResolutionContext:
        """Build source context for a file position.

        Args:
            file_uri: LSP file URI where resolution is requested.
            offset: Source offset where resolution is requested.
            word: Identifier-like word under the cursor.

        Returns:
            Resolution context containing the innermost scope and containers.
        """
        scope = self._innermost_scope(file_uri, offset)
        function_name = self._scope_name_for_kind(scope, ScopeKind.FUNCTION)
        container_name = self._container_name(scope)

        return ResolutionContext(
            file_uri=file_uri,
            offset=offset,
            word=word,
            scope=scope,
            function_name=function_name,
            container_name=container_name,
        )

    def _lookup_local(self, file_uri: str, function_name: str, name: str) -> Symbol | None:
        matches = [
            symbol
            for symbol in self._index.symbol_table.symbols
            if symbol.file_uri == file_uri
            and symbol.container_name == function_name
            and symbol.name == name
            and symbol.kind == SymbolKind.LOCAL
        ]
        return matches[-1] if matches else None

    def _locals_in_function(self, file_uri: str, function_name: str) -> tuple[Symbol, ...]:
        return tuple(
            symbol
            for symbol in self._index.symbol_table.symbols
            if symbol.file_uri == file_uri
            and symbol.container_name == function_name
            and symbol.kind == SymbolKind.LOCAL
        )

    def _lookup_member(self, type_name: str, name: str) -> Symbol | None:
        for symbol in self._members_for_type(type_name):
            if symbol.name == name:
                return symbol

        return None

    def _members_for_type(self, type_name: str) -> tuple[Symbol, ...]:
        members: list[Symbol] = []
        visited: set[str] = set()
        current_type: str | None = type_name

        while current_type is not None and current_type not in visited:
            visited.add(current_type)
            members.extend(
                symbol
                for symbol in self._index.symbol_table.symbols
                if symbol.container_name == current_type
                and symbol.kind
                in {
                    SymbolKind.EVENT,
                    SymbolKind.FIELD,
                    SymbolKind.FUNCTION,
                }
            )
            current_type_symbol = self.resolve_type(current_type)
            current_type = (
                current_type_symbol.type_name if current_type_symbol is not None else None
            )

        return tuple(members)

    def _lookup_global(self, name: str, current_file_uri: str) -> Symbol | None:
        matches = [
            symbol for symbol in self._index.symbol_table.global_symbols() if symbol.name == name
        ]

        for symbol in matches:
            if symbol.file_uri == current_file_uri:
                return symbol

        return matches[0] if matches else None

    def _innermost_scope(self, file_uri: str, offset: int) -> Scope | None:
        scopes = [
            scope
            for scope in self._index.symbol_table.scopes
            if scope.file_uri == file_uri and _contains_offset(scope.range, offset)
        ]
        return min(
            scopes,
            key=lambda scope: scope.range.end.offset - scope.range.start.offset,
            default=None,
        )

    def _container_name(self, scope: Scope | None) -> str | None:
        current = scope

        while current is not None:
            if current.kind in {ScopeKind.CLASS, ScopeKind.STATE}:
                return current.name

            current = self._parent_scope(current)

        return None

    def _scope_name_for_kind(self, scope: Scope | None, kind: ScopeKind) -> str | None:
        current = scope

        while current is not None:
            if current.kind == kind:
                return current.name

            current = self._parent_scope(current)

        return None

    def _parent_scope(self, scope: Scope) -> Scope | None:
        if scope.parent_name is None:
            return None

        for candidate in self._index.symbol_table.scopes:
            if (
                candidate.file_uri == scope.file_uri
                and candidate.name == scope.parent_name
                and _contains_offset(candidate.range, scope.range.start.offset)
            ):
                return candidate

        return None


def _contains_offset(range_: SourceRange, offset: int) -> bool:
    return range_.start.offset <= offset <= range_.end.offset


def _deduplicate_symbols(symbols: list[Symbol]) -> list[Symbol]:
    seen: set[tuple[str, SymbolKind, str, int, int]] = set()
    deduplicated: list[Symbol] = []

    for symbol in symbols:
        key = (
            symbol.name,
            symbol.kind,
            symbol.file_uri,
            symbol.range.start.offset,
            symbol.range.end.offset,
        )

        if key in seen:
            continue

        seen.add(key)
        deduplicated.append(symbol)

    return deduplicated
