"""Inheritance lookup helpers."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind


@dataclass(frozen=True)
class InheritanceIndex:
    """Class inheritance relationships discovered in the symbol table.

    Attributes:
        base_to_derived: Mapping from base class name to derived class names.
        derived_to_base: Mapping from derived class name to base class name.
    """

    base_to_derived: dict[str, tuple[str, ...]]
    derived_to_base: dict[str, str]

    @classmethod
    def build(cls, symbols: tuple[Symbol, ...]) -> InheritanceIndex:
        """Build inheritance lookup maps from class symbols.

        Args:
            symbols: Project symbols.

        Returns:
            Class inheritance index.
        """
        base_to_derived: defaultdict[str, list[str]] = defaultdict(list)
        derived_to_base: dict[str, str] = {}

        for symbol in symbols:
            if symbol.kind != SymbolKind.CLASS or symbol.type_name is None:
                continue

            base_to_derived[symbol.type_name].append(symbol.name)
            derived_to_base[symbol.name] = symbol.type_name

        return cls(
            base_to_derived={
                base_name: tuple(derived_names)
                for base_name, derived_names in base_to_derived.items()
            },
            derived_to_base=derived_to_base,
        )

    def derived_classes(self, base_name: str) -> tuple[str, ...]:
        """Return classes derived from a base class.

        Args:
            base_name: Base class name.

        Returns:
            Derived class names in project order.
        """
        return self.base_to_derived.get(base_name, ())

    def base_class(self, derived_name: str) -> str | None:
        """Return the base class for a derived class.

        Args:
            derived_name: Derived class name.

        Returns:
            Base class name, or ``None`` when there is no indexed base.
        """
        return self.derived_to_base.get(derived_name)
