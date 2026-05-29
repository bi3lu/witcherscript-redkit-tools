import json
from pathlib import Path
from typing import Any, cast

from witcherscript_langserver.parser.ast import (
    ClassDecl,
    Decl,
    FunctionDecl,
    ImportDecl,
    Module,
    ParamDecl,
    StateDecl,
    Statement,
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


def _module_snapshot(module: Module) -> dict[str, Any]:
    return {
        "imports": [_import_snapshot(import_decl) for import_decl in module.imports],
        "declarations": [_decl_snapshot(declaration) for declaration in module.declarations],
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


def _statement_snapshot(statement: Statement) -> dict[str, Any]:
    return {
        "kind": statement.kind,
        "has_expression": statement.expression_range is not None,
    }


def _load_snapshot(name: str) -> dict[str, Any]:
    return cast("dict[str, Any]", json.loads((SNAPSHOT_DIR / name).read_text(encoding="utf-8")))
