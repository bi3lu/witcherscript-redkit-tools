"""Data models for the tolerant WitcherScript AST."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from witcherscript_langserver.parser.tokens import SourceRange


@dataclass(frozen=True)
class LiteralExpr:
    """Literal expression.

    Attributes:
        value: Literal source value.
        literal_kind: Literal category.
        range: Source range covered by the expression.
    """

    value: str
    literal_kind: LiteralKind
    range: SourceRange


@dataclass(frozen=True)
class IdentifierExpr:
    """Identifier expression.

    Attributes:
        name: Referenced identifier name.
        range: Source range covered by the expression.
    """

    name: str
    range: SourceRange


@dataclass(frozen=True)
class UnaryExpr:
    """Unary expression.

    Attributes:
        operator: Unary operator lexeme.
        operand: Operand expression.
        range: Source range covered by the expression.
    """

    operator: str
    operand: Expr
    range: SourceRange


@dataclass(frozen=True)
class BinaryExpr:
    """Binary expression.

    Attributes:
        left: Left operand expression.
        operator: Binary operator lexeme.
        right: Right operand expression.
        range: Source range covered by the expression.
    """

    left: Expr
    operator: str
    right: Expr
    range: SourceRange


@dataclass(frozen=True)
class AssignmentExpr:
    """Assignment expression.

    Attributes:
        target: Assignment target expression.
        operator: Assignment operator lexeme.
        value: Assigned value expression.
        range: Source range covered by the expression.
    """

    target: Expr
    operator: str
    value: Expr
    range: SourceRange


@dataclass(frozen=True)
class CallExpr:
    """Function or method call expression.

    Attributes:
        callee: Called expression.
        args: Call arguments in source order.
        range: Source range covered by the expression.
    """

    callee: Expr
    args: list[Expr]
    range: SourceRange


@dataclass(frozen=True)
class MemberAccessExpr:
    """Member access expression.

    Attributes:
        target: Target expression before the dot.
        member: Accessed member name.
        range: Source range covered by the expression.
    """

    target: Expr
    member: str
    range: SourceRange


@dataclass(frozen=True)
class ArrayAccessExpr:
    """Array access expression.

    Attributes:
        target: Indexed target expression.
        index: Index expression.
        range: Source range covered by the expression.
    """

    target: Expr
    index: Expr
    range: SourceRange


@dataclass(frozen=True)
class GroupingExpr:
    """Parenthesized expression.

    Attributes:
        expression: Inner expression.
        range: Source range covered by the expression.
    """

    expression: Expr
    range: SourceRange


@dataclass(frozen=True)
class ErrorExpr:
    """Placeholder expression used when expression parsing recovers from an error.

    Attributes:
        range: Source range covered by the unexpected token.
    """

    range: SourceRange


type LiteralKind = Literal["bool", "none", "null", "number", "string"]
type Expr = (
    ArrayAccessExpr
    | AssignmentExpr
    | BinaryExpr
    | CallExpr
    | ErrorExpr
    | GroupingExpr
    | IdentifierExpr
    | LiteralExpr
    | MemberAccessExpr
    | UnaryExpr
)


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
        initializer: Parsed initializer expression, when present.
    """

    name: str
    type_name: str | None
    initializer_range: SourceRange | None
    range: SourceRange
    flags: list[str] = field(default_factory=list)
    initializer: Expr | None = None


@dataclass(frozen=True)
class Statement:
    """Minimal statement node used for body structure.

    Attributes:
        kind: Structural statement kind.
        range: Source range covered by the statement.
        expression_range: Source range of the statement expression, when tracked.
        expression: Parsed statement expression, when tracked.
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
    expression: Expr | None = None


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
