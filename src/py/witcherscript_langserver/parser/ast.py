"""AST models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from witcherscript_langserver.parser.tokens import SourceRange


@dataclass(frozen=True)
class ImportDecl:
    """Import declaration."""

    target: str
    range: SourceRange


@dataclass(frozen=True)
class ParamDecl:
    """Function parameter declaration."""

    name: str
    type_name: str | None
    range: SourceRange
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VarDecl:
    """Variable declaration."""

    name: str
    type_name: str | None
    initializer_range: SourceRange | None
    range: SourceRange
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Statement:
    """Minimal statement node used for body structure."""

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
    """Function or event declaration."""

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
    """Class declaration."""

    name: str
    base_name: str | None
    members: list[Decl]
    range: SourceRange
    flags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StateDecl:
    """State declaration."""

    name: str
    parent_name: str | None
    members: list[Decl]
    range: SourceRange


type Decl = ClassDecl | FunctionDecl | StateDecl | VarDecl


@dataclass(frozen=True)
class Module:
    """Parsed WitcherScript module."""

    imports: list[ImportDecl]
    declarations: list[Decl]
    range: SourceRange
