from collections.abc import Callable
from pathlib import Path
from typing import cast

from lsprotocol import types

from witcherscript_langserver.server import WitcherScriptLanguageServer, create_server


def test_server_registers_minimal_lsp_features() -> None:
    server = create_server()
    features = server.protocol.fm.features

    assert types.INITIALIZE in features
    assert types.INITIALIZED in features
    assert types.TEXT_DOCUMENT_DID_OPEN in features
    assert types.TEXT_DOCUMENT_DID_CHANGE in features
    assert types.TEXT_DOCUMENT_DID_SAVE in features
    assert types.WORKSPACE_DID_CHANGE_WATCHED_FILES in features


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
) -> Callable[[object], None]:
    return cast("Callable[[object], None]", server.protocol.fm.features[feature_name])
