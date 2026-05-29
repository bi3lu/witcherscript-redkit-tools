"""Data models for the tolerant WitcherScript AST."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from witcherscript_langserver.parser.tokens import SourceRange


@dataclass(frozen=True)
class ImportDecl:
    """Import declaration.

    Attributes:
        target: Imported path or module name as written in source.
        range: Source range covered by the import declaration.
    """

    target: str
    range: SourceRange


@dataclass(frozen=True)
class ParamDecl:
    """Function parameter declaration.

    Attributes:
        name: Parameter name.
        type_name: Parameter type name, when it is present in source.
        range: Source range covered by the parameter declaration.
        flags: Parameter modifiers, such as ``optional`` or ``out``.
    """

    name: str
    type_name: str | None
    range: SourceRange
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VarDecl:
    """Variable declaration.

    Attributes:
        name: Variable or property name.
        type_name: Declared type name, when it is present in source.
        initializer_range: Source range of the initializer expression, when present.
        range: Source range covered by the declaration.
        flags: Declaration modifiers, such as ``default``.
    """

    name: str
    type_name: str | None
    initializer_range: SourceRange | None
    range: SourceRange
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Statement:
    """Minimal statement node used for body structure.

    Attributes:
        kind: Structural statement kind.
        range: Source range covered by the statement.
        expression_range: Source range of the statement expression, when tracked.
    """

    kind: Literal[
        "block",
        "break",
        "continue",
        "expression",
        "for",
        "if",
        "return",
        "switch",
        "var",
        "while",
    ]
    range: SourceRange
    expression_range: SourceRange | None = None


@dataclass(frozen=True)
class FunctionDecl:
    """Function or event declaration.

    Attributes:
        name: Function or event name.
        params: Function parameters in source order.
        return_type: Declared return type, when one is present.
        body_range: Source range of the function body, or ``None`` for declarations.
        range: Source range covered by the full declaration.
        flags: Function modifiers and event markers.
        locals: Local variable declarations discovered in the function body.
        statements: Minimal statement nodes discovered in the function body.
    """

    name: str
    params: list[ParamDecl]
    return_type: str | None
    body_range: SourceRange | None
    range: SourceRange
    flags: list[str] = field(default_factory=list)
    locals: list[VarDecl] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)


@dataclass(frozen=True)
class ClassDecl:
    """Class declaration.

    Attributes:
        name: Class name.
        base_name: Base class name from an ``extends`` clause, when present.
        members: Nested class members in source order.
        range: Source range covered by the full class declaration.
        flags: Class modifiers, such as ``abstract`` or ``statemachine``.
    """

    name: str
    base_name: str | None
    members: list[Decl]
    range: SourceRange
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StateDecl:
    """State declaration.

    Attributes:
        name: State name.
        parent_name: Parent state name from an ``in`` clause, when present.
        members: Nested state members in source order.
        range: Source range covered by the full state declaration.
    """

    name: str
    parent_name: str | None
    members: list[Decl]
    range: SourceRange


type Decl = ClassDecl | FunctionDecl | StateDecl | VarDecl


@dataclass(frozen=True)
class Module:
    """Parsed WitcherScript module.

    Attributes:
        imports: Top-level imports in source order.
        declarations: Top-level declarations in source order.
        range: Source range covered by the parsed module.
    """

    imports: list[ImportDecl]
    declarations: list[Decl]
    range: SourceRange
