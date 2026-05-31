"""Tests for WitcherScript signature help."""

from pathlib import Path

from lsprotocol import types

from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.lsp.signature_help import signature_help


def test_signature_help_returns_function_parameters(tmp_path: Path) -> None:
    source = _write_signature_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    result = signature_help(index, source, uri, _position_after(source, "make("))

    assert result is not None
    assert result.active_signature == 0
    assert result.active_parameter == 0
    assert [signature.label for signature in result.signatures] == [
        "make(other: Base, count: int): Base"
    ]


def test_signature_help_tracks_active_parameter(tmp_path: Path) -> None:
    source = _write_signature_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    result = signature_help(index, source, uri, _position_after(source, "make(local, "))

    assert result is not None
    assert result.active_parameter == 1
    assert result.signatures[0].parameters is not None
    assert [parameter.label for parameter in result.signatures[0].parameters] == [
        "other: Base",
        "count: int",
    ]


def test_signature_help_resolves_member_call_signature(tmp_path: Path) -> None:
    source = _write_signature_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    result = signature_help(index, source, uri, _position_after(source, "local.merge(1, "))

    assert result is not None
    assert result.active_parameter == 1
    assert [signature.label for signature in result.signatures] == [
        "merge(left: int, right: string): Player"
    ]


def test_signature_help_prefers_innermost_call(tmp_path: Path) -> None:
    source = _write_signature_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    result = signature_help(
        index,
        source,
        uri,
        _position_after(source, "make(local.merge(1, "),
    )

    assert result is not None
    assert result.active_parameter == 1
    assert [signature.label for signature in result.signatures] == [
        "merge(left: int, right: string): Player"
    ]


def test_signature_help_returns_none_outside_call(tmp_path: Path) -> None:
    source = _write_signature_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    result = signature_help(index, source, uri, _position_after(source, "var local"))

    assert result is None


def _write_signature_workspace(root: Path) -> str:
    scripts = root / "scripts"
    scripts.mkdir()
    source = """
class Base
{
    function merge(left : int, right : string) : Player
    {
    }
}

class Player extends Base
{
    function make(other : Base, count : int) : Base
    {
        return other;
    }

    function run()
    {
        var local : Base;
        make(local, 1);
        local.merge(1, "x");
        make(local.merge(1, "x"), 1);
    }
}
""".lstrip()
    (scripts / "player.ws").write_text(source, encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return source


def _position_after(source: str, needle: str) -> types.Position:
    offset = source.index(needle) + len(needle)
    line = source.count("\n", 0, offset)
    line_start = source.rfind("\n", 0, offset)
    character = offset if line_start == -1 else offset - line_start - 1
    return types.Position(line=line, character=character)
