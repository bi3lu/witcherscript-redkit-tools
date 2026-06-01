"""Integration-style tests for editor-visible LSP behavior."""

from collections.abc import Callable
from pathlib import Path
from typing import cast

from lsprotocol import types

from witcherscript_langserver.server import WitcherScriptLanguageServer, create_server


def test_lsp_client_initialize_open_and_diagnostics_flow(tmp_path: Path) -> None:
    """Exercise initialize, didOpen, and publishDiagnostics as a client flow."""
    player, _base, source = _write_workspace(tmp_path)
    server = create_server()
    published = _capture_published_diagnostics(server)

    _request(server, types.INITIALIZE)(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(),
            process_id=123,
            root_uri=tmp_path.as_uri(),
        )
    )
    _request(server, types.INITIALIZED)(types.InitializedParams())
    _open(server, player, source.replace("return other;", "return missing;"))

    assert server.initialized
    assert server.workspace_root_uri == tmp_path.as_uri()
    assert server.document_text(player.as_uri()).endswith("return missing;\n    }\n}\n")
    assert [diagnostic.code for diagnostic in published[-1].diagnostics] == ["WS3004"]


def test_lsp_client_completion_hover_definition_references_and_signature_help(
    tmp_path: Path,
) -> None:
    """Exercise the main editor requests used by the VS Code client."""
    player, base, source = _write_workspace(tmp_path)
    server = _initialized_server(tmp_path)
    _open(server, player, source)

    completion = cast(
        "types.CompletionList",
        _request(server, types.TEXT_DOCUMENT_COMPLETION)(
            types.CompletionParams(
                text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
                position=_position_after(source, "local."),
            )
        ),
    )
    assert {"merge", "shared"} <= {item.label for item in completion.items}

    hover = cast(
        "types.Hover",
        _request(server, types.TEXT_DOCUMENT_HOVER)(
            types.HoverParams(
                text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
                position=_position_of(source, "shared"),
            )
        ),
    )
    assert isinstance(hover.contents, types.MarkupContent)
    assert "shared: int" in hover.contents.value

    definition = cast(
        "types.Location",
        _request(server, types.TEXT_DOCUMENT_DEFINITION)(
            types.DefinitionParams(
                text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
                position=_position_of(source, "Base"),
            )
        ),
    )
    assert definition.uri == base.as_uri()

    references = cast(
        "list[types.Location]",
        _request(server, types.TEXT_DOCUMENT_REFERENCES)(
            types.ReferenceParams(
                text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
                position=_position_of(source, "Base"),
                context=types.ReferenceContext(include_declaration=True),
            )
        ),
    )
    assert len(references) >= 3
    assert {reference.uri for reference in references} == {player.as_uri(), base.as_uri()}

    signature_help = cast(
        "types.SignatureHelp",
        _request(server, types.TEXT_DOCUMENT_SIGNATURE_HELP)(
            types.SignatureHelpParams(
                text_document=types.TextDocumentIdentifier(uri=player.as_uri()),
                position=_position_after(source, "local.merge(1, "),
            )
        ),
    )
    assert signature_help.active_parameter == 1
    assert signature_help.signatures[0].label == "merge(left: int, right: int): int"


def _write_workspace(root: Path) -> tuple[Path, Path, str]:
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
        local.shared;
        local.merge(1, 2);
        return other;
    }
}
""".lstrip()
    base.write_text(
        """
class Base
{
    var shared : int;

    function merge(left : int, right : int) : int
    {
        return left;
    }
}
""".lstrip(),
        encoding="utf-8",
    )
    player.write_text(source, encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return player, base, source


def _initialized_server(root: Path) -> WitcherScriptLanguageServer:
    server = create_server()
    _request(server, types.INITIALIZE)(
        types.InitializeParams(
            capabilities=types.ClientCapabilities(),
            process_id=123,
            root_uri=root.as_uri(),
        )
    )
    return server


def _open(server: WitcherScriptLanguageServer, path: Path, source: str) -> None:
    _request(server, types.TEXT_DOCUMENT_DID_OPEN)(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=path.as_uri(),
                language_id="witcherscript",
                version=1,
                text=source,
            )
        )
    )


def _request(
    server: WitcherScriptLanguageServer,
    feature_name: str,
) -> Callable[[object], object]:
    return cast("Callable[[object], object]", server.protocol.fm.features[feature_name])


def _capture_published_diagnostics(
    server: WitcherScriptLanguageServer,
) -> list[types.PublishDiagnosticsParams]:
    published: list[types.PublishDiagnosticsParams] = []

    def capture(params: types.PublishDiagnosticsParams) -> None:
        """Store published diagnostics for later assertions."""
        published.append(params)

    server.text_document_publish_diagnostics = capture  # type: ignore[method-assign]
    return published


def _position_of(source: str, needle: str, occurrence: int = 1) -> types.Position:
    offset = -1
    search_from = 0

    for _ in range(occurrence):
        offset = source.index(needle, search_from)
        search_from = offset + len(needle)

    return _position_at_offset(source, offset)


def _position_after(source: str, needle: str, occurrence: int = 1) -> types.Position:
    offset = -1
    search_from = 0

    for _ in range(occurrence):
        offset = source.index(needle, search_from) + len(needle)
        search_from = offset

    return _position_at_offset(source, offset)


def _position_at_offset(source: str, offset: int) -> types.Position:
    line = source.count("\n", 0, offset)
    line_start = source.rfind("\n", 0, offset)
    character = offset if line_start == -1 else offset - line_start - 1
    return types.Position(line=line, character=character)
