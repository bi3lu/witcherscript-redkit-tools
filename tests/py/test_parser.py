"""Tests for WitcherScript parser snapshots and recovery behavior."""

import json
from pathlib import Path
from typing import Any, cast

from witcherscript_langserver.parser.ast import (
    ArrayAccessExpr,
    AssignmentExpr,
    BinaryExpr,
    CallExpr,
    ClassDecl,
    Decl,
    ErrorExpr,
    Expr,
    FunctionDecl,
    GroupingExpr,
    IdentifierExpr,
    ImportDecl,
    LiteralExpr,
    MemberAccessExpr,
    Module,
    ParamDecl,
    StateDecl,
    Statement,
    UnaryExpr,
    VarDecl,
)
from witcherscript_langserver.parser.parser import parse

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_DIR = ROOT / "tests" / "py" / "snapshots" / "parser"


def test_parser_showcase_snapshot() -> None:
    assert _parse_snapshot("samples/scripts/valid/lexer_showcase.ws") == _load_snapshot(
        "lexer_showcase_ast.json"
    )


def test_parser_language_guide_features_snapshot() -> None:
    assert _parse_snapshot("samples/scripts/valid/language_guide_features.ws") == _load_snapshot(
        "language_guide_features_ast.json"
    )


def test_parser_recovers_after_broken_declaration_snapshot() -> None:
    assert _snapshot_source("class Broken { var x : int function ok() {}") == _load_snapshot(
        "broken_recovery_ast.json"
    )


def test_parser_expression_showcase_snapshot() -> None:
    assert _expression_parse_snapshot(
        "samples/scripts/valid/expression_showcase.ws"
    ) == _load_snapshot("expression_showcase_ast.json")


def test_parser_expression_recovery_snapshot() -> None:
    source = """
class BrokenExpressions
{
    function run() : int
    {
        var index : int = 1 + ;
        return index +;
    }

    var afterBrokenExpression : int = 2;
}
"""

    assert _expression_snapshot_source(source) == _load_snapshot("expression_recovery_ast.json")


def _parse_snapshot(relative_path: str) -> dict[str, Any]:
    return _snapshot_source((ROOT / relative_path).read_text(encoding="utf-8"))


def _snapshot_source(source: str) -> dict[str, Any]:
    result = parse(source)
    return {
        "module": _module_snapshot(result.module),
        "diagnostics": [
            {
                "code": diagnostic.code,
                "message": diagnostic.message,
            }
            for diagnostic in result.diagnostics
        ],
    }


def _expression_parse_snapshot(relative_path: str) -> dict[str, Any]:
    return _expression_snapshot_source((ROOT / relative_path).read_text(encoding="utf-8"))


def _expression_snapshot_source(source: str) -> dict[str, Any]:
    result = parse(source)
    return {
        "module": _expression_module_snapshot(result.module),
        "diagnostics": [
            {
                "code": diagnostic.code,
                "message": diagnostic.message,
            }
            for diagnostic in result.diagnostics
        ],
    }


def _module_snapshot(module: Module) -> dict[str, Any]:
    return {
        "imports": [_import_snapshot(import_decl) for import_decl in module.imports],
        "declarations": [_decl_snapshot(declaration) for declaration in module.declarations],
    }


def _expression_module_snapshot(module: Module) -> dict[str, Any]:
    return {
        "imports": [_import_snapshot(import_decl) for import_decl in module.imports],
        "declarations": [
            _expression_decl_snapshot(declaration) for declaration in module.declarations
        ],
    }


def _import_snapshot(import_decl: ImportDecl) -> dict[str, Any]:
    return {
        "kind": "ImportDecl",
        "target": import_decl.target,
    }


def _decl_snapshot(declaration: Decl) -> dict[str, Any]:
    if isinstance(declaration, ClassDecl):
        return {
            "kind": "ClassDecl",
            "name": declaration.name,
            "base_name": declaration.base_name,
            "flags": declaration.flags,
            "members": [_decl_snapshot(member) for member in declaration.members],
        }

    if isinstance(declaration, StateDecl):
        return {
            "kind": "StateDecl",
            "name": declaration.name,
            "parent_name": declaration.parent_name,
            "members": [_decl_snapshot(member) for member in declaration.members],
        }

    if isinstance(declaration, FunctionDecl):
        return {
            "kind": "FunctionDecl",
            "name": declaration.name,
            "flags": declaration.flags,
            "params": [_param_snapshot(param) for param in declaration.params],
            "return_type": declaration.return_type,
            "has_body": declaration.body_range is not None,
            "locals": [_var_snapshot(local) for local in declaration.locals],
            "statements": [_statement_snapshot(statement) for statement in declaration.statements],
        }

    return _var_snapshot(declaration)


def _expression_decl_snapshot(declaration: Decl) -> dict[str, Any]:
    snapshot = _decl_snapshot(declaration)

    if isinstance(declaration, ClassDecl | StateDecl):
        snapshot["members"] = [_expression_decl_snapshot(member) for member in declaration.members]

    elif isinstance(declaration, FunctionDecl):
        snapshot["locals"] = [_expression_var_snapshot(local) for local in declaration.locals]
        snapshot["statements"] = [
            _expression_statement_snapshot(statement) for statement in declaration.statements
        ]

    elif isinstance(declaration, VarDecl):
        snapshot = _expression_var_snapshot(declaration)

    return snapshot


def _param_snapshot(param: ParamDecl) -> dict[str, Any]:
    return {
        "name": param.name,
        "type_name": param.type_name,
        "flags": param.flags,
    }


def _var_snapshot(var_decl: VarDecl) -> dict[str, Any]:
    return {
        "kind": "VarDecl",
        "name": var_decl.name,
        "type_name": var_decl.type_name,
        "flags": var_decl.flags,
        "has_initializer": var_decl.initializer_range is not None,
    }


def _expression_var_snapshot(var_decl: VarDecl) -> dict[str, Any]:
    snapshot = _var_snapshot(var_decl)
    snapshot["initializer"] = (
        _expression_snapshot(var_decl.initializer) if var_decl.initializer is not None else None
    )
    return snapshot


def _statement_snapshot(statement: Statement) -> dict[str, Any]:
    return {
        "kind": statement.kind,
        "has_expression": statement.expression_range is not None,
    }


def _expression_statement_snapshot(statement: Statement) -> dict[str, Any]:
    snapshot = _statement_snapshot(statement)
    snapshot["expression"] = (
        _expression_snapshot(statement.expression) if statement.expression is not None else None
    )
    return snapshot


def _expression_snapshot(expression: Expr) -> dict[str, Any]:
    if isinstance(expression, LiteralExpr):
        return {
            "kind": "LiteralExpr",
            "literal_kind": expression.literal_kind,
            "value": expression.value,
        }

    if isinstance(expression, IdentifierExpr):
        return {
            "kind": "IdentifierExpr",
            "name": expression.name,
        }

    if isinstance(expression, UnaryExpr):
        return {
            "kind": "UnaryExpr",
            "operator": expression.operator,
            "operand": _expression_snapshot(expression.operand),
        }

    if isinstance(expression, BinaryExpr):
        return {
            "kind": "BinaryExpr",
            "operator": expression.operator,
            "left": _expression_snapshot(expression.left),
            "right": _expression_snapshot(expression.right),
        }

    if isinstance(expression, AssignmentExpr):
        return {
            "kind": "AssignmentExpr",
            "operator": expression.operator,
            "target": _expression_snapshot(expression.target),
            "value": _expression_snapshot(expression.value),
        }

    if isinstance(expression, CallExpr):
        return {
            "kind": "CallExpr",
            "callee": _expression_snapshot(expression.callee),
            "args": [_expression_snapshot(arg) for arg in expression.args],
        }

    if isinstance(expression, MemberAccessExpr):
        return {
            "kind": "MemberAccessExpr",
            "target": _expression_snapshot(expression.target),
            "member": expression.member,
        }

    if isinstance(expression, ArrayAccessExpr):
        return {
            "kind": "ArrayAccessExpr",
            "target": _expression_snapshot(expression.target),
            "index": _expression_snapshot(expression.index),
        }

    if isinstance(expression, GroupingExpr):
        return {
            "kind": "GroupingExpr",
            "expression": _expression_snapshot(expression.expression),
        }

    if isinstance(expression, ErrorExpr):
        return {
            "kind": "ErrorExpr",
        }

    raise AssertionError(f"Unhandled expression type: {type(expression)!r}")


def _load_snapshot(name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((SNAPSHOT_DIR / name).read_text(encoding="utf-8")))
