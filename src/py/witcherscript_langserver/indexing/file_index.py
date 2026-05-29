"""Per-file AST and symbol index."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from witcherscript_langserver.analysis.symbol_table import (
    Scope,
    ScopeKind,
    Symbol,
    SymbolKind,
    TypeReference,
)
from witcherscript_langserver.parser.ast import (
    ClassDecl,
    Decl,
    FunctionDecl,
    Module,
    ParamDecl,
    StateDecl,
    Statement,
    VarDecl,
)
from witcherscript_langserver.parser.errors import SyntaxDiagnostic
from witcherscript_langserver.parser.parser import parse
from witcherscript_langserver.parser.tokens import SourceRange


@dataclass(frozen=True)
class FileIndex:
    """Index data for one WitcherScript source file.

    Attributes:
        path: Local file path.
        uri: LSP file URI.
        module: Parsed module tree.
        imports: Import targets declared in the module.
        symbols: Symbols extracted from the module.
        scopes: Structural scopes extracted from the module.
        type_references: Type references extracted from declarations.
        diagnostics: Recoverable lexer and parser diagnostics for the file.
    """

    path: Path
    uri: str
    module: Module
    imports: tuple[str, ...]
    symbols: tuple[Symbol, ...]
    scopes: tuple[Scope, ...]
    type_references: tuple[TypeReference, ...]
    diagnostics: tuple[SyntaxDiagnostic, ...]


def build_file_index(path: Path, uri: str, source: str) -> FileIndex:
    """Build an index for one WitcherScript source file.

    Args:
        path: Local file path.
        uri: LSP file URI.
        source: File source text.

    Returns:
        Parsed file index containing AST, symbols, and diagnostics.
    """
    result = parse(source)
    return FileIndex(
        path=path,
        uri=uri,
        module=result.module,
        imports=tuple(import_decl.target for import_decl in result.module.imports),
        symbols=tuple(_module_symbols(result.module, uri)),
        scopes=tuple(_module_scopes(result.module, uri)),
        type_references=tuple(_module_type_references(result.module, uri)),
        diagnostics=tuple(result.diagnostics),
    )


def _module_symbols(module: Module, file_uri: str) -> list[Symbol]:
    symbols: list[Symbol] = []

    for declaration in module.declarations:
        symbols.extend(_declaration_symbols(declaration, file_uri, container_name=None))

    return symbols


def _declaration_symbols(
    declaration: Decl,
    file_uri: str,
    container_name: str | None,
) -> list[Symbol]:
    if isinstance(declaration, ClassDecl):
        symbols = [
            Symbol(
                name=declaration.name,
                kind=SymbolKind.CLASS,
                file_uri=file_uri,
                range=declaration.range,
                selection_range=declaration.range,
                container_name=container_name,
                type_name=declaration.base_name,
            )
        ]

        for member in declaration.members:
            symbols.extend(_declaration_symbols(member, file_uri, container_name=declaration.name))

        return symbols

    if isinstance(declaration, StateDecl):
        symbols = [
            Symbol(
                name=declaration.name,
                kind=SymbolKind.STATE,
                file_uri=file_uri,
                range=declaration.range,
                selection_range=declaration.range,
                container_name=container_name,
                type_name=declaration.parent_name,
            )
        ]

        for member in declaration.members:
            symbols.extend(_declaration_symbols(member, file_uri, container_name=declaration.name))

        return symbols

    if isinstance(declaration, FunctionDecl):
        kind = SymbolKind.EVENT if "event" in declaration.flags else SymbolKind.FUNCTION
        symbols = [
            Symbol(
                name=declaration.name,
                kind=kind,
                file_uri=file_uri,
                range=declaration.range,
                selection_range=declaration.range,
                container_name=container_name,
                type_name=declaration.return_type,
            )
        ]

        for param in declaration.params:
            symbols.append(_param_symbol(param, file_uri, declaration.name))

        for local in declaration.locals:
            symbols.append(_local_var_symbol(local, file_uri, declaration.name))

        return symbols

    if isinstance(declaration, VarDecl):
        return [
            Symbol(
                name=declaration.name,
                kind=SymbolKind.FIELD,
                file_uri=file_uri,
                range=declaration.range,
                selection_range=declaration.range,
                container_name=container_name,
                type_name=declaration.type_name,
            )
        ]

    return []


def _local_var_symbol(var_decl: VarDecl, file_uri: str, container_name: str) -> Symbol:
    return Symbol(
        name=var_decl.name,
        kind=SymbolKind.LOCAL,
        file_uri=file_uri,
        range=var_decl.range,
        selection_range=var_decl.range,
        container_name=container_name,
        type_name=var_decl.type_name,
    )


def _param_symbol(param: ParamDecl, file_uri: str, container_name: str) -> Symbol:
    return Symbol(
        name=param.name,
        kind=SymbolKind.LOCAL,
        file_uri=file_uri,
        range=param.range,
        selection_range=param.range,
        container_name=container_name,
        type_name=param.type_name,
    )


def _module_scopes(module: Module, file_uri: str) -> list[Scope]:
    scopes = [
        Scope(
            name="<global>",
            kind=ScopeKind.GLOBAL,
            file_uri=file_uri,
            range=module.range,
            parent_name=None,
        )
    ]

    for declaration in module.declarations:
        scopes.extend(_declaration_scopes(declaration, file_uri, parent_name="<global>"))

    return scopes


def _declaration_scopes(declaration: Decl, file_uri: str, parent_name: str) -> list[Scope]:
    if isinstance(declaration, ClassDecl):
        scopes = [
            Scope(
                name=declaration.name,
                kind=ScopeKind.CLASS,
                file_uri=file_uri,
                range=declaration.range,
                parent_name=parent_name,
            )
        ]
        for member in declaration.members:
            scopes.extend(_declaration_scopes(member, file_uri, parent_name=declaration.name))

        return scopes

    if isinstance(declaration, StateDecl):
        scopes = [
            Scope(
                name=declaration.name,
                kind=ScopeKind.STATE,
                file_uri=file_uri,
                range=declaration.range,
                parent_name=parent_name,
            )
        ]
        for member in declaration.members:
            scopes.extend(_declaration_scopes(member, file_uri, parent_name=declaration.name))

        return scopes

    if isinstance(declaration, FunctionDecl):
        scopes = [
            Scope(
                name=declaration.name,
                kind=ScopeKind.FUNCTION,
                file_uri=file_uri,
                range=declaration.range,
                parent_name=parent_name,
            )
        ]
        scopes.extend(_block_scopes(declaration.statements, file_uri, parent_name=declaration.name))
        return scopes

    return []


def _block_scopes(
    statements: list[Statement],
    file_uri: str,
    parent_name: str,
) -> list[Scope]:
    scopes: list[Scope] = []

    for index, statement in enumerate(statements):
        if statement.kind != "block":
            continue

        scopes.append(
            Scope(
                name=f"{parent_name}#block{index}",
                kind=ScopeKind.BLOCK,
                file_uri=file_uri,
                range=statement.range,
                parent_name=parent_name,
            )
        )

    return scopes


def _module_type_references(module: Module, file_uri: str) -> list[TypeReference]:
    references: list[TypeReference] = []

    for declaration in module.declarations:
        references.extend(_declaration_type_references(declaration, file_uri, container_name=None))

    return references


def _declaration_type_references(
    declaration: Decl,
    file_uri: str,
    container_name: str | None,
) -> list[TypeReference]:
    references: list[TypeReference] = []

    if isinstance(declaration, ClassDecl):
        references.extend(
            _type_references(declaration.base_name, file_uri, declaration.range, None)
        )
        for member in declaration.members:
            references.extend(
                _declaration_type_references(member, file_uri, container_name=declaration.name)
            )

        return references

    if isinstance(declaration, StateDecl):
        references.extend(
            _type_references(declaration.parent_name, file_uri, declaration.range, None)
        )
        for member in declaration.members:
            references.extend(
                _declaration_type_references(member, file_uri, container_name=declaration.name)
            )

        return references

    if isinstance(declaration, FunctionDecl):
        references.extend(
            _type_references(declaration.return_type, file_uri, declaration.range, container_name)
        )
        for param in declaration.params:
            references.extend(
                _type_references(param.type_name, file_uri, param.range, declaration.name)
            )
        for local in declaration.locals:
            references.extend(
                _declaration_type_references(local, file_uri, container_name=declaration.name)
            )

        return references

    if isinstance(declaration, VarDecl):
        references.extend(
            _type_references(declaration.type_name, file_uri, declaration.range, container_name)
        )

    return references


def _type_references(
    type_name: str | None,
    file_uri: str,
    range_: SourceRange,
    container_name: str | None,
) -> list[TypeReference]:
    if type_name is None:
        return []

    return [
        TypeReference(name=name, file_uri=file_uri, range=range_, container_name=container_name)
        for name in _type_reference_names(type_name)
    ]


def _type_reference_names(type_name: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", type_name))
