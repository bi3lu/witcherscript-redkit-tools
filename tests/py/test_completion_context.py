"""Tests for context-aware WitcherScript completion."""

from pathlib import Path

from lsprotocol import types

from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.lsp.completion import completions


def test_completion_filters_to_types_after_colon(tmp_path: Path) -> None:
    source = _write_completion_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    labels = _labels(index, uri, source, "var typed : ")

    assert {"Base", "Player"} <= labels
    assert "run" not in labels
    assert "value" not in labels
    assert "return" not in labels


def test_completion_filters_to_classes_after_extends(tmp_path: Path) -> None:
    source = _write_completion_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    labels = _labels(index, uri, source, "class Child extends ")

    assert {"Base", "Player"} <= labels
    assert "QuestState" not in labels
    assert "run" not in labels
    assert "class" not in labels


def test_completion_includes_locals_and_members_inside_function(tmp_path: Path) -> None:
    source = _write_completion_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    labels = _labels(index, uri, source, "        return ", occurrence=2)

    assert {"value", "local", "ownField", "shared", "inherited", "Base", "Player"} <= labels
    assert "return" in labels
    assert "class" not in labels


def test_completion_returns_members_after_dot(tmp_path: Path) -> None:
    source = _write_completion_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    local_labels = _labels(index, uri, source, "        local.")
    this_labels = _labels(index, uri, source, "        this.")

    assert {"shared", "inherited"} <= local_labels
    assert "ownField" not in local_labels
    assert {"ownField", "shared", "inherited", "run"} <= this_labels
    assert "return" not in this_labels
    assert "Base" not in this_labels


def test_completion_returns_import_targets(tmp_path: Path) -> None:
    source = _write_completion_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    uri = (tmp_path / "scripts" / "player.ws").resolve().as_uri()

    labels = _labels(index, uri, source, 'import "')

    assert {"base", "quest"} <= labels
    assert "Player" not in labels
    assert "class" not in labels


def _labels(
    index: ProjectIndex,
    uri: str,
    source: str,
    needle: str,
    occurrence: int = 1,
) -> set[str]:
    completion = completions(index, uri, source, _position_after(source, needle, occurrence))
    return {item.label for item in completion.items}


def _write_completion_workspace(root: Path) -> str:
    scripts = root / "scripts"
    scripts.mkdir()
    source = """
import "

class Base
{
    var shared : int;

    function inherited() : int
    {
        return 0;
    }
}

state QuestState
{
}

class Player extends Base
{
    var ownField : string;
    var typed : 

    function run(value : string) : Base
    {
        var local : Base;
        local.;
        this.;
        return local;
    }
}

class Child extends 
{
}
""".lstrip()
    (scripts / "player.ws").write_text(source, encoding="utf-8")
    (scripts / "base.ws").write_text("class ExternalBase {}\n", encoding="utf-8")
    (scripts / "quest.ws").write_text("state ExternalQuest {}\n", encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return source


def _position_after(source: str, needle: str, occurrence: int = 1) -> types.Position:
    offset = -1
    search_from = 0

    for _ in range(occurrence):
        offset = source.index(needle, search_from) + len(needle)
        search_from = offset

    line = source.count("\n", 0, offset)
    line_start = source.rfind("\n", 0, offset)
    character = offset if line_start == -1 else offset - line_start - 1
    return types.Position(line=line, character=character)
