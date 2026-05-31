"""Tests for project-level semantic diagnostics."""

from pathlib import Path

from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex


def test_semantic_diagnostics_report_duplicates_and_unknown_types(tmp_path: Path) -> None:
    script = _write_workspace(
        tmp_path,
        """
class Player extends MissingBase
{
    var title : MissingType;
    var title : string;

    function tick() {}
    function tick() {}
}

class Player {}
""".lstrip(),
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    diagnostics = index.diagnostics_for_uri(script.as_uri())

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS3001", "Duplicate class symbol 'Player'."),
        ("WS3001", "Duplicate field symbol 'title'."),
        ("WS3001", "Duplicate function symbol 'tick'."),
        ("WS3003", "Base class 'MissingBase' is not defined."),
        ("WS3002", "Type 'MissingType' is not defined."),
    ]


def test_semantic_diagnostics_report_expression_errors(tmp_path: Path) -> None:
    script = _write_workspace(
        tmp_path,
        """
class Player
{
    function make(value : int) {}

    function run()
    {
        missingValue;
        make(1, 2);
        nope();
    }
}
""".lstrip(),
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    diagnostics = index.diagnostics_for_uri(script.as_uri())

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS3004", "Identifier 'missingValue' is not defined."),
        ("WS3005", "Function 'make' expects 1 argument(s), got 2."),
        ("WS3004", "Function 'nope' is not defined."),
    ]


def test_semantic_diagnostics_report_unknown_members(tmp_path: Path) -> None:
    script = _write_workspace(
        tmp_path,
        """
class Base
{
    var shared : int;

    function owner() : Player
    {
    }
}

class Player extends Base
{
    var ownField : string;

    function run()
    {
        var local : Base;
        local.shared;
        local.missingBaseMember;
        local.owner().ownField;
        local.owner().missingPlayerMember;
    }
}
""".lstrip(),
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    diagnostics = index.diagnostics_for_uri(script.as_uri())

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS3006", "Type 'Base' has no member 'missingBaseMember'."),
        ("WS3006", "Type 'Player' has no member 'missingPlayerMember'."),
    ]


def test_semantic_diagnostics_report_type_mismatches(tmp_path: Path) -> None:
    script = _write_workspace(
        tmp_path,
        """
class Base {}

class Player extends Base
{
    function make(other : Base, count : int) : Base
    {
        return "bad";
    }

    function run()
    {
        var local : Base;
        var count : int = "bad";
        local = "bad";
        make("bad", "two");
    }
}
""".lstrip(),
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    diagnostics = index.diagnostics_for_uri(script.as_uri())

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS3009", "Return type expects 'Base', got 'string'."),
        ("WS3008", "Initializer for 'count' expects type 'int', got 'string'."),
        ("WS3008", "Cannot assign type 'string' to 'Base'."),
        ("WS3007", "Argument 'other' expects type 'Base', got 'string'."),
        ("WS3007", "Argument 'count' expects type 'int', got 'string'."),
    ]


def test_semantic_diagnostics_report_import_and_inheritance_errors(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True)
    player = scripts / "player.ws"
    player.write_text(
        """
import "missing";

state QuestState {}

class Player extends QuestState {}

class CycleA extends CycleB {}
class CycleB extends CycleA {}
""".lstrip(),
        encoding="utf-8",
    )
    (scripts / "existing.ws").write_text("class Existing {}\n", encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    diagnostics = index.diagnostics_for_uri(player.as_uri())

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("WS3011", "Class 'Player' cannot extend state 'QuestState'."),
        ("WS3011", "Inheritance cycle detected: CycleA -> CycleB -> CycleA."),
        ("WS3011", "Inheritance cycle detected: CycleB -> CycleA -> CycleB."),
        ("WS3010", "Import 'missing' could not be resolved."),
    ]


def test_semantic_diagnostics_accept_known_project_types_and_builtins(tmp_path: Path) -> None:
    script = _write_workspace(
        tmp_path,
        """
class Base {}

class Player extends Base
{
    var title : string;
    var owner : Base;

    function make(value : int) : Base
    {
        var local : Base;
        return local;
    }
}
""".lstrip(),
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    assert index.diagnostics_for_uri(script.as_uri()) == ()


def _write_workspace(root: Path, source: str) -> Path:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "player.ws"
    script.write_text(source, encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return script
