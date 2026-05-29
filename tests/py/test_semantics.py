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
""".lstrip(),
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    diagnostics = index.diagnostics_for_uri(script.as_uri())

    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
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
