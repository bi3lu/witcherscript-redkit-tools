"""Tests for context-aware WitcherScript name resolution."""

from pathlib import Path

from lsprotocol import types

from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import SymbolKind
from witcherscript_langserver.analysis.types import TypeLookupContext, TypeLookupService
from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.lsp.completion import completions
from witcherscript_langserver.lsp.definition import definition
from witcherscript_langserver.lsp.hover import hover


def test_resolver_prefers_locals_over_fields_and_globals(tmp_path: Path) -> None:
    source = _write_resolution_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    resolver = NameResolver(index)
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    result = resolver.resolve(uri, _offset_of(source, "value;"), "value")

    assert result is not None
    assert result.source == "local"
    assert result.symbol.kind == SymbolKind.LOCAL
    assert result.symbol.container_name == "run"
    assert result.symbol.type_name == "string"


def test_resolver_finds_class_members_and_inherited_members(tmp_path: Path) -> None:
    source = _write_resolution_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    resolver = NameResolver(index)
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    field = resolver.resolve(uri, _offset_of(source, "ownField;"), "ownField")
    inherited_field = resolver.resolve(uri, _offset_of(source, "shared;"), "shared")
    inherited_method = resolver.resolve(uri, _offset_of(source, "inherited();"), "inherited")

    assert field is not None
    assert field.source == "member"
    assert field.symbol.kind == SymbolKind.FIELD
    assert field.symbol.container_name == "Player"

    assert inherited_field is not None
    assert inherited_field.source == "inherited_member"
    assert inherited_field.symbol.kind == SymbolKind.FIELD
    assert inherited_field.symbol.container_name == "Base"

    assert inherited_method is not None
    assert inherited_method.source == "inherited_member"
    assert inherited_method.symbol.kind == SymbolKind.FUNCTION
    assert inherited_method.symbol.container_name == "Base"


def test_resolver_handles_this_and_type_references(tmp_path: Path) -> None:
    source = _write_resolution_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    resolver = NameResolver(index)
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    this_result = resolver.resolve(uri, _offset_of(source, "this;"), "this")
    type_result = resolver.resolve(uri, _offset_of(source, ": Base"), "Base")

    assert this_result is not None
    assert this_result.source == "this"
    assert this_result.symbol.name == "Player"
    assert this_result.symbol.kind == SymbolKind.CLASS

    assert type_result is not None
    assert type_result.symbol.name == "Base"
    assert type_result.symbol.kind == SymbolKind.CLASS


def test_lsp_features_use_context_aware_resolution(tmp_path: Path) -> None:
    source = _write_resolution_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    player = tmp_path / "scripts" / "player.ws"
    uri = player.resolve().as_uri()

    assert index.diagnostics == ()

    local_definition = definition(index, source, uri, _position_of(source, "value;"))
    inherited_hover = hover(index, source, uri, _position_of(source, "shared;"))
    completion = completions(index, uri, source, _position_of(source, "return", occurrence=2))
    labels = {item.label for item in completion.items}

    assert local_definition is not None
    assert local_definition.uri == uri
    assert inherited_hover is not None
    assert isinstance(inherited_hover.contents, types.MarkupContent)
    assert "shared: int" in inherited_hover.contents.value
    assert {"value", "local", "ownField", "shared", "inherited", "Base", "Player"} <= labels


def test_type_lookup_resolves_member_chains_and_call_return_types(tmp_path: Path) -> None:
    source = _write_resolution_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()
    lookup = TypeLookupService(index.symbol_table)
    context = TypeLookupContext(
        file_uri=uri,
        offset=_offset_of(source, "local.owner().ownField"),
        function_name="run",
        container_name="Player",
    )

    assert lookup.type_of_expression_source("local.owner()", context) == "Player"
    assert lookup.type_of_expression_source("local.owner().ownField", context) == "string"
    assert lookup.member_for_type("Player", "shared") is not None
    assert lookup.member_for_type("Player", "missing") is None


def _write_resolution_workspace(root: Path) -> str:
    scripts = root / "scripts"
    scripts.mkdir()
    source = """
class Base
{
    var shared : int;

    function inherited() : int
    {
        return 0;
    }

    function owner() : Player
    {
    }
}

class Player extends Base
{
    var value : int;
    var ownField : string;

    function run(value : string) : Base
    {
        var local : Base;
        value;
        local;
        ownField;
        shared;
        inherited();
        local.owner().ownField;
        this;
        return local;
    }
}
""".lstrip()
    (scripts / "player.ws").write_text(source, encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return source


def _offset_of(source: str, needle: str, occurrence: int = 1) -> int:
    offset = -1
    search_from = 0

    for _ in range(occurrence):
        offset = source.index(needle, search_from)
        search_from = offset + len(needle)

    return offset


def _position_of(source: str, needle: str, occurrence: int = 1) -> types.Position:
    offset = _offset_of(source, needle, occurrence)
    line = source.count("\n", 0, offset)
    line_start = source.rfind("\n", 0, offset)
    character = offset if line_start == -1 else offset - line_start - 1
    return types.Position(line=line, character=character)
