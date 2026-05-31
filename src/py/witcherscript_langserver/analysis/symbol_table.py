"""Project-wide symbol table models."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from witcherscript_langserver.parser.tokens import SourceRange


class SymbolKind(StrEnum):
    """Kinds of named symbols understood by the language server."""

    CLASS = "class"
    EVENT = "event"
    FIELD = "field"
    FUNCTION = "function"
    LOCAL = "local"
    STATE = "state"


class ScopeKind(StrEnum):
    """Kinds of scopes used by the structural symbol index."""

    BLOCK = "block"
    CLASS = "class"
    FUNCTION = "function"
    GLOBAL = "global"
    STATE = "state"


@dataclass(frozen=True)
class Symbol:
    """Named declaration indexed from WitcherScript source.

    Attributes:
        name: Symbol name.
        kind: Symbol kind.
        file_uri: LSP file URI where the symbol is declared.
        range: Source range covered by the declaration.
        selection_range: Source range used when selecting the symbol name.
        container_name: Optional containing class, state, or function name.
        type_name: Declared type, return type, base class, or parent state.
    """

    name: str
    kind: SymbolKind
    file_uri: str
    range: SourceRange
    selection_range: SourceRange
    container_name: str | None
    type_name: str | None


@dataclass(frozen=True)
class Scope:
    """Structural scope discovered in a WitcherScript file.

    Attributes:
        name: Scope name.
        kind: Scope kind.
        file_uri: LSP file URI where the scope appears.
        range: Source range covered by the scope.
        parent_name: Optional containing scope name.
    """

    name: str
    kind: ScopeKind
    file_uri: str
    range: SourceRange
    parent_name: str | None


@dataclass(frozen=True)
class TypeReference:
    """Reference from a declaration to a type-like symbol.

    Attributes:
        name: Referenced type name.
        file_uri: LSP file URI where the reference appears.
        range: Source range that currently approximates the reference location.
        container_name: Optional containing class, state, or function name.
    """

    name: str
    file_uri: str
    range: SourceRange
    container_name: str | None


@dataclass(frozen=True)
class CallableParameter:
    """Callable parameter data used for signature help.

    Attributes:
        name: Parameter name.
        type_name: Parameter type name, when declared.
    """

    name: str
    type_name: str | None


@dataclass(frozen=True)
class CallableSignature:
    """Callable declaration data used for call validation.

    Attributes:
        name: Callable name.
        file_uri: LSP file URI where the callable is declared.
        range: Source range covered by the declaration.
        container_name: Optional containing class or state name.
        parameters: Declared parameters in source order.
        return_type: Declared return type, when one is present.
    """

    name: str
    file_uri: str
    range: SourceRange
    container_name: str | None
    parameters: tuple[CallableParameter, ...]
    return_type: str | None

    @property
    def parameter_count(self) -> int:
        """Return the number of declared parameters.

        Returns:
            Parameter count used by call diagnostics.
        """
        return len(self.parameters)


@dataclass(frozen=True)
class SymbolTable:
    """Project-wide lookup table for symbols, scopes, and type references.

    Attributes:
        symbols: All indexed symbols in project order.
        scopes: All indexed scopes in project order.
        type_references: Type-like references found in declarations.
        callable_signatures: Function and event signatures.
    """

    symbols: tuple[Symbol, ...]
    scopes: tuple[Scope, ...]
    type_references: tuple[TypeReference, ...]
    callable_signatures: tuple[CallableSignature, ...] = ()

    @classmethod
    def build(
        cls,
        symbols: Iterable[Symbol],
        scopes: Iterable[Scope],
        type_references: Iterable[TypeReference],
        callable_signatures: Iterable[CallableSignature] = (),
    ) -> SymbolTable:
        """Build a symbol table from project index fragments.

        Args:
            symbols: Symbols collected from indexed files.
            scopes: Scopes collected from indexed files.
            type_references: Type references collected from indexed files.
            callable_signatures: Callable signatures collected from indexed files.

        Returns:
            Immutable symbol table.
        """
        return cls(
            symbols=tuple(symbols),
            scopes=tuple(scopes),
            type_references=tuple(type_references),
            callable_signatures=tuple(callable_signatures),
        )

    def symbols_for_file(self, file_uri: str) -> tuple[Symbol, ...]:
        """Return symbols declared in one file.

        Args:
            file_uri: LSP file URI.

        Returns:
            Symbols declared in the requested file.
        """
        return tuple(symbol for symbol in self.symbols if symbol.file_uri == file_uri)

    def lookup(self, name: str) -> tuple[Symbol, ...]:
        """Return all symbols with a matching name.

        Args:
            name: Symbol name to find.

        Returns:
            Matching symbols in project order.
        """
        return tuple(symbol for symbol in self.symbols if symbol.name == name)

    def lookup_type(self, name: str) -> Symbol | None:
        """Return the first class or state symbol matching a type name.

        Args:
            name: Type name to resolve.

        Returns:
            Matching class/state symbol, or ``None`` when unresolved.
        """
        for symbol in self.symbols:
            if symbol.name == name and symbol.kind in {SymbolKind.CLASS, SymbolKind.STATE}:
                return symbol

        return None

    def global_symbols(self) -> tuple[Symbol, ...]:
        """Return project-wide symbols useful for completion and definition.

        Returns:
            Top-level classes, states, functions, and events.
        """
        return tuple(
            symbol
            for symbol in self.symbols
            if symbol.container_name is None
            and symbol.kind
            in {
                SymbolKind.CLASS,
                SymbolKind.EVENT,
                SymbolKind.FUNCTION,
                SymbolKind.STATE,
            }
        )

    def by_name(self) -> dict[str, tuple[Symbol, ...]]:
        """Group symbols by name.

        Returns:
            Mapping from symbol name to symbols.
        """
        grouped: defaultdict[str, list[Symbol]] = defaultdict(list)

        for symbol in self.symbols:
            grouped[symbol.name].append(symbol)

        return {name: tuple(items) for name, items in grouped.items()}

    def lookup_callable(self, name: str) -> tuple[CallableSignature, ...]:
        """Return callable signatures by name.

        Args:
            name: Function or event name.

        Returns:
            Matching callable signatures.
        """
        return tuple(signature for signature in self.callable_signatures if signature.name == name)
