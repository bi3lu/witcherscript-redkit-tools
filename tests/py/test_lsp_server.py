"""Tests for WitcherScript language server feature registration and handlers."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

from lsprotocol import types

from witcherscript_langserver.server import (
    REFRESH_INDEX_COMMAND,
    WitcherScriptLanguageServer,
    create_server,
)


def test_server_registers_minimal_lsp_features() -> None:
    server = create_server()
    features = server.protocol.fm.features

    assert types.INITIALIZE in features
    assert types.INITIALIZED in features
    assert types.TEXT_DOCUMENT_DID_OPEN in features
    assert types.TEXT_DOCUMENT_DID_CHANGE in features
    assert types.TEXT_DOCUMENT_DID_SAVE in features
    assert types.WORKSPACE_DID_CHANGE_WATCHED_FILES in features
    assert types.WORKSPACE_EXECUTE_COMMAND in features
    assert types.TEXT_DOCUMENT_DOCUMENT_SYMBOL in features
    assert types.WORKSPACE_SYMBOL in features
    assert types.TEXT_DOCUMENT_DEFINITION in features
    assert types.TEXT_DOCUMENT_COMPLETION in features
    assert types.TEXT_DOCUMENT_HOVER in features
    assert types.TEXT_DOCUMENT_REFERENCES in features


def test_initialize_and_initialized_update_server_state() -> None:
    server = create_server()
    root_uri = "file:///workspace"

    _feature(server, types.INITIALIZE)(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(),
            process_id=123,
            root_uri=root_uri,
        )
    )
    _feature(server, types.INITIALIZED)(types.InitializedParams())

    assert server.workspace_root_uri == root_uri
    assert server.initialized


def test_initialize_loads_workspace_index(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "player.ws").write_text("class Player {}", encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[project]\nname = "LspFixture"\n\n[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    server = create_server()

    _feature(server, types.INITIALIZE)(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(),
            process_id=123,
            root_uri=tmp_path.as_uri(),
        )
    )

    assert server.workspace_root_uri == tmp_path.as_uri()
    assert server.workspace_state.config is not None
    assert server.workspace_state.config.project.name == "LspFixture"
    assert len(server.workspace_state.index.files) == 1


def test_did_open_caches_document_and_publishes_diagnostics() -> None:
    server = create_server()
    published = _capture_published_diagnostics(server)
    uri = "file:///workspace/scripts/player.ws"

    _feature(server, types.TEXT_DOCUMENT_DID_OPEN)(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=uri,
                language_id="witcherscript",
                version=1,
                text="class Player {",
            )
        )
    )

    assert server.document_text(uri) == "class Player {"
    assert len(published) == 1
    assert published[0].uri == uri
    assert [diagnostic.code for diagnostic in published[0].diagnostics] == ["WS2002"]


def test_did_open_publishes_semantic_diagnostics(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    player = scripts / "player.ws"
    source = "class Player extends MissingBase {}"
    player.write_text(source, encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    server = _initialized_server(tmp_path)
    published = _capture_published_diagnostics(server)

    _open_document(server, player, source)

    assert [diagnostic.code for diagnostic in published[0].diagnostics] == ["WS3003"]


def test_did_change_updates_document_and_republishes_diagnostics() -> None:
    server = create_server()
    published = _capture_published_diagnostics(server)
    uri = "file:///workspace/scripts/player.ws"

    _feature(server, types.TEXT_DOCUMENT_DID_CHANGE)(
        types.DidChangeTextDocumentParams(
            text_document=types.VersionedTextDocumentIdentifier(uri=uri, version=2),
            content_changes=[types.TextDocumentContentChangeWholeDocument(text="class Player {}")],
        )
    )

    assert server.document_text(uri) == "class Player {}"
    assert len(published) == 1
    assert published[0].diagnostics == []


def test_did_save_uses_saved_text_when_available() -> None:
    server = create_server()
    published = _capture_published_diagnostics(server)
    uri = "file:///workspace/scripts/player.ws"

    server.cache_document(uri, "class Player {}")
    _feature(server, types.TEXT_DOCUMENT_DID_SAVE)(
        types.DidSaveTextDocumentParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            text='class Player { var title : string = "oops\n}',
        )
    )

    assert server.document_text(uri) == 'class Player { var title : string = "oops\n}'
    assert len(published) == 1
    assert [diagnostic.code for diagnostic in published[0].diagnostics] == ["WS1002", "WS2001"]


def test_watched_file_changes_refresh_workspace_index(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    player = scripts / "player.ws"
    player.write_text("class Player {}", encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    server = create_server()
    _feature(server, types.INITIALIZE)(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(),
            process_id=123,
            root_uri=tmp_path.as_uri(),
        )
    )

    player.write_text("class Updated {}", encoding="utf-8")
    _feature(server, types.WORKSPACE_DID_CHANGE_WATCHED_FILES)(
        types.DidChangeWatchedFilesParams(
            changes=[types.FileEvent(uri=player.as_uri(), type=types.FileChangeType.Changed)]
        )
    )

    assert [symbol.name for symbol in server.workspace_state.index.files[player].symbols] == [
        "Updated"
    ]

    player.unlink()
    _feature(server, types.WORKSPACE_DID_CHANGE_WATCHED_FILES)(
        types.DidChangeWatchedFilesParams(
            changes=[types.FileEvent(uri=player.as_uri(), type=types.FileChangeType.Deleted)]
        )
    )

    assert player not in server.workspace_state.index.files


def test_refresh_index_command_reloads_generated_config(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    generated = tmp_path / "generated-by-redkit"
    scripts.mkdir()
    generated.mkdir()
    player = scripts / "player.ws"
    quest = generated / "quest.ws"
    player.write_text("class Player {}", encoding="utf-8")
    quest.write_text("class Quest {}", encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    server = _initialized_server(tmp_path)

    assert set(server.workspace_state.index.files) == {player}

    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts", "generated-by-redkit"]\n',
        encoding="utf-8",
    )
    result = _feature(server, types.WORKSPACE_EXECUTE_COMMAND)(
        types.ExecuteCommandParams(command=REFRESH_INDEX_COMMAND)
    )

    assert result == {"indexedFiles": 2, "indexedSymbols": 2}
    assert set(server.workspace_state.index.files) == {player, quest}


def test_refresh_index_command_preserves_open_document_edits(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    player = scripts / "player.ws"
    player.write_text("class Player {}", encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    server = _initialized_server(tmp_path)
    published = _capture_published_diagnostics(server)

    _open_document(server, player, "class Unsaved {}")
    result = _feature(server, types.WORKSPACE_EXECUTE_COMMAND)(
        types.ExecuteCommandParams(command=REFRESH_INDEX_COMMAND)
    )

    assert result == {"indexedFiles": 1, "indexedSymbols": 1}
    assert [symbol.name for symbol in server.workspace_state.index.files[player].symbols] == [
        "Unsaved"
    ]
    assert published[-1].uri == player.as_uri()


def test_document_symbols_returns_outline(tmp_path: Path) -> None:
    player, _base, source = _write_lsp_feature_workspace(tmp_path)
    server = _initialized_server(tmp_path)
    _open_document(server, player, source)

    result = _feature(server, types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)(
        types.DocumentSymbolParams(text_document=types.TextDocumentIdentifier(uri=player.as_uri()))
    )

    symbols = cast("list[types.DocumentSymbol]", result)
    assert [(symbol.name, symbol.kind) for symbol in symbols] == [
        ("Player", types.SymbolKind.Class)
    ]
    assert symbols[0].children is not None
    assert [(child.name, child.kind) for child in symbols[0].children] == [
        ("title", types.SymbolKind.Field),
        ("make", types.SymbolKind.Function),
    ]


def test_workspace_symbols_searches_project_symbols(tmp_path: Path) -> None:
    _player, _base, _source = _write_lsp_feature_workspace(tmp_path)
    server = _initialized_server(tmp_path)

    result = _feature(server, types.WORKSPACE_SYMBOL)(types.WorkspaceSymbolParams(query="Base"))

    symbols = cast("list[types.WorkspaceSymbol]", result)
    assert [(symbol.name, symbol.kind) for symbol in symbols] == [("Base", types.SymbolKind.Class)]


def test_definition_hover_completion_and_references(tmp_path: Path) -> None:
    player, base, source = _write_lsp_feature_workspace(tmp_path)
    server = _initialized_server(tmp_path)
    _open_document(server, player, source)

    definition_result = _feature(server, types.TEXT_DOCUMENT_DEFINITION)(
        types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
            position=_position_of(source, "Base"),
        )
    )
    location = cast("types.Location", definition_result)
    assert location.uri == base.as_uri()

    hover_result = _feature(server, types.TEXT_DOCUMENT_HOVER)(
        types.HoverParams(
            text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
            position=_position_of(source, "title"),
        )
    )
    hover = cast("types.Hover", hover_result)
    assert isinstance(hover.contents, types.MarkupContent)
    assert "title: string" in hover.contents.value

    completion_result = _feature(server, types.TEXT_DOCUMENT_COMPLETION)(
        types.CompletionParams(
            text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
            position=_position_of(source, "return"),
        )
    )
    completion = cast("types.CompletionList", completion_result)
    labels = {item.label for item in completion.items}
    assert {"return", "var", "Player", "Base", "title", "make", "local"} <= labels
    assert "class" not in labels

    references_result = _feature(server, types.TEXT_DOCUMENT_REFERENCES)(
        types.ReferenceParams(
            text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
            position=_position_of(source, "Base"),
            context=types.ReferenceContext(include_declaration=True),
        )
    )
    references = cast("list[types.Location]", references_result)
    assert len([reference for reference in references if reference.uri == player.as_uri()]) == 4
    assert len([reference for reference in references if reference.uri == base.as_uri()]) == 1


def _capture_published_diagnostics(
    server: WitcherScriptLanguageServer,
) -> list[types.PublishDiagnosticsParams]:
    published: list[types.PublishDiagnosticsParams] = []

    def capture(params: types.PublishDiagnosticsParams) -> None:
        """Store published diagnostics for later test assertions."""
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


def _open_document(server: WitcherScriptLanguageServer, path: Path, source: str) -> None:
    _feature(server, types.TEXT_DOCUMENT_DID_OPEN)(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=path.as_uri(),
                language_id="witcherscript",
                version=1,
                text=source,
            )
        )
    )


def _write_lsp_feature_workspace(root: Path) -> tuple[Path, Path, str]:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    base = scripts / "base.ws"
    player = scripts / "player.ws"
    source = """
class Player extends Base
{
    var title : string;

    function make(other : Base) : Base
    {
        var local : Base;
        return local;
    }
}
""".lstrip()
    base.write_text("class Base {}\n", encoding="utf-8")
    player.write_text(source, encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return player, base, source


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
