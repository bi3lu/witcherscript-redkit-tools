"""End-to-end tests for fixture workspaces and LSP behavior."""

import json
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
from lsprotocol import types

from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex
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
from witcherscript_langserver.server import WitcherScriptLanguageServer, create_server

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "samples" / "fixtures"
SNAPSHOT_DIR = ROOT / "tests" / "py" / "snapshots" / "e2e"


def test_basic_project_indexes_symbols_and_serves_symbol_requests() -> None:
    root = FIXTURE_ROOT / "basic_project"
    player = root / "scripts" / "player.ws"
    server = _initialized_server(root)

    assert server.workspace_state.config is not None
    assert server.workspace_state.config.project.name == "BasicFixture"
    assert {path.name for path in server.workspace_state.index.files} == {
        "base.ws",
        "player.ws",
        "quest.ws",
    }
    assert server.workspace_state.index.diagnostics == ()

    document_result = _feature(server, types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)(
        types.DocumentSymbolParams(text_document=types.TextDocumentIdentifier(uri=player.as_uri()))
    )
    document_symbols = cast("list[types.DocumentSymbol]", document_result)
    assert [(symbol.name, symbol.kind) for symbol in document_symbols] == [
        ("PlayerCharacter", types.SymbolKind.Class)
    ]
    assert document_symbols[0].children is not None
    assert [(child.name, child.kind) for child in document_symbols[0].children] == [
        ("title", types.SymbolKind.Field),
        ("makeBase", types.SymbolKind.Function),
    ]

    workspace_result = _feature(server, types.WORKSPACE_SYMBOL)(
        types.WorkspaceSymbolParams(query="Quest")
    )
    workspace_symbols = cast("list[types.WorkspaceSymbol]", workspace_result)
    assert [(symbol.name, symbol.kind) for symbol in workspace_symbols] == [
        ("QuestState", types.SymbolKind.Class)
    ]


def test_broken_project_publishes_expected_diagnostics() -> None:
    root = FIXTURE_ROOT / "broken_project"
    broken = root / "scripts" / "broken.ws"
    semantic = root / "scripts" / "semantic.ws"
    server = _initialized_server(root)
    published = _capture_published_diagnostics(server)

    _open_document(server, broken)
    _open_document(server, semantic)

    diagnostics_by_uri = {
        publication.uri: [diagnostic.code for diagnostic in publication.diagnostics]
        for publication in published
    }
    assert diagnostics_by_uri[broken.as_uri()] == ["WS1002", "WS2001"]
    assert diagnostics_by_uri[semantic.as_uri()] == ["WS3003", "WS3002", "WS3004", "WS3004"]


def test_basic_project_completion_and_definition() -> None:
    root = FIXTURE_ROOT / "basic_project"
    base = root / "scripts" / "base.ws"
    player = root / "scripts" / "player.ws"
    source = player.read_text(encoding="utf-8")
    server = _initialized_server(root)
    _open_document(server, player)

    completion_result = _feature(server, types.TEXT_DOCUMENT_COMPLETION)(
        types.CompletionParams(
            text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
            position=_position_of(source, "return"),
        )
    )
    completion = cast("types.CompletionList", completion_result)
    labels = {item.label for item in completion.items}
    assert {
        "class",
        "function",
        "BaseActor",
        "PlayerCharacter",
        "QuestState",
        "makeBase",
        "local",
    } <= labels

    definition_result = _feature(server, types.TEXT_DOCUMENT_DEFINITION)(
        types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
            position=_position_of(source, "BaseActor"),
        )
    )
    location = cast("types.Location", definition_result)
    assert location.uri == base.as_uri()


def test_basic_project_player_ast_snapshot() -> None:
    source = (FIXTURE_ROOT / "basic_project" / "scripts" / "player.ws").read_text(encoding="utf-8")

    assert _snapshot_source(source) == _load_snapshot("basic_project_player_ast.json")


@pytest.mark.performance
def test_larger_project_indexing_performance(tmp_path: Path) -> None:
    root = tmp_path / "larger_project"
    shutil.copytree(FIXTURE_ROOT / "larger_project", root)
    scripts = root / "scripts"

    for index in range(100):
        previous = "Actor04" if index == 0 else f"Generated{index - 1:03d}"
        (scripts / f"generated_{index:03d}.ws").write_text(
            f"class Generated{index:03d} extends {previous}\n{{\n    var next : {previous};\n}}\n",
            encoding="utf-8",
        )

    started = time.perf_counter()
    project_index = ProjectIndex.build(load_workspace_config(root))
    elapsed = time.perf_counter() - started

    assert len(project_index.files) == 105
    assert len(project_index.symbols) == 210
    assert project_index.diagnostics == ()
    assert elapsed < 5.0


def _capture_published_diagnostics(
    server: WitcherScriptLanguageServer,
) -> list[types.PublishDiagnosticsParams]:
    published: list[types.PublishDiagnosticsParams] = []

    def capture(params: types.PublishDiagnosticsParams) -> None:
        published.append(params)

    server.text_document_publish_diagnostics = capture  # type: ignore[method-assign]
    return published


def _feature(
    server: WitcherScriptLanguageServer,
    feature_name: str,
) -> Callable[[object], object]:
    return cast("Callable[[object], object]", server.protocol.fm.features[feature_name])


def _initialized_server(root: Path) -> WitcherScriptLanguageServer:
    server = create_server()
    _feature(server, types.INITIALIZE)(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(),
            process_id=123,
            root_uri=root.as_uri(),
        )
    )
    return server


def _open_document(server: WitcherScriptLanguageServer, path: Path) -> None:
    _feature(server, types.TEXT_DOCUMENT_DID_OPEN)(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=path.as_uri(),
                language_id="witcherscript",
                version=1,
                text=path.read_text(encoding="utf-8"),
            )
        )
    )


def _position_of(source: str, needle: str, occurrence: int = 1) -> types.Position:
    offset = -1
    search_from = 0

    for _ in range(occurrence):
        offset = source.index(needle, search_from)
        search_from = offset + len(needle)

    line = source.count("\n", 0, offset)
    line_start = source.rfind("\n", 0, offset)
    character = offset if line_start == -1 else offset - line_start - 1
    return types.Position(line=line, character=character)


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
