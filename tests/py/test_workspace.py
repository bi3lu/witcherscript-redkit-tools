"""Tests for workspace configuration, scanning, and URI handling."""

from pathlib import Path

from witcherscript_langserver.analysis.symbol_table import SymbolKind
from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex, scan_script_files
from witcherscript_langserver.workspace import WorkspaceState, normalize_file_uri, path_from_uri


def test_load_workspace_config_resolves_toml_paths(tmp_path: Path) -> None:
    _write_workspace(tmp_path)

    config = load_workspace_config(tmp_path)

    assert config.config_path == tmp_path / "witcherscript.toml"
    assert config.project.name == "WorkspaceFixture"
    assert config.redkit.game_directory == tmp_path / "game"
    assert config.scripts.source_roots == (tmp_path / "scripts",)
    assert config.scripts.vanilla_roots == (tmp_path / "vanilla" / "scripts",)
    assert config.scripts.exclude == ("**/bin/**", "**/.cache/**", "**/generated/**")


def test_scan_script_files_respects_roots_and_excludes(tmp_path: Path) -> None:
    files = _write_workspace(tmp_path)
    config = load_workspace_config(tmp_path)

    assert scan_script_files(config) == (
        files["player"],
        files["quest"],
        files["vanilla"],
    )


def test_project_index_builds_file_indexes_and_symbols(tmp_path: Path) -> None:
    files = _write_workspace(tmp_path)
    config = load_workspace_config(tmp_path)

    index = ProjectIndex.build(config)

    assert set(index.files) == {files["player"], files["quest"], files["vanilla"]}
    assert [(symbol.name, symbol.kind, symbol.container_name) for symbol in index.symbols] == [
        ("Player", SymbolKind.CLASS, None),
        ("name", SymbolKind.FIELD, "Player"),
        ("tick", SymbolKind.FUNCTION, "Player"),
        ("QuestState", SymbolKind.STATE, None),
        ("BaseCharacter", SymbolKind.CLASS, None),
    ]
    assert index.diagnostics == ()


def test_workspace_state_initializes_from_root_uri(tmp_path: Path) -> None:
    files = _write_workspace(tmp_path)
    workspace = WorkspaceState()

    workspace.initialize(tmp_path.as_uri())

    assert workspace.root_uri == tmp_path.as_uri()
    assert workspace.root_path == tmp_path
    assert workspace.config is not None
    assert set(workspace.index.files) == {files["player"], files["quest"], files["vanilla"]}


def test_workspace_state_updates_and_removes_file(tmp_path: Path) -> None:
    files = _write_workspace(tmp_path)
    workspace = WorkspaceState()
    workspace.initialize(tmp_path.as_uri())

    workspace.update_file(files["player"].as_uri(), "class Updated {}")
    assert [symbol.name for symbol in workspace.index.files[files["player"]].symbols] == ["Updated"]

    workspace.remove_file(files["player"].as_uri())
    assert files["player"] not in workspace.index.files


def test_path_from_uri_handles_local_file_uri(tmp_path: Path) -> None:
    path = tmp_path / "scripts" / "player.ws"

    assert path_from_uri(path.as_uri()) == path
    assert normalize_file_uri(path.as_uri()) == path.resolve().as_uri()
    assert path_from_uri("untitled:Scratch.ws") is None
    assert normalize_file_uri("untitled:Scratch.ws") == "untitled:Scratch.ws"


def _write_workspace(root: Path) -> dict[str, Path]:
    scripts = root / "scripts"
    vanilla = root / "vanilla" / "scripts"
    scripts.mkdir(parents=True)
    vanilla.mkdir(parents=True)
    (scripts / "bin").mkdir()
    (scripts / ".cache").mkdir()
    (scripts / "generated").mkdir()
    (root / "game").mkdir()

    files = {
        "player": scripts / "player.ws",
        "quest": scripts / "quest.ws",
        "vanilla": vanilla / "base.ws",
        "bin": scripts / "bin" / "skip.ws",
        "cache": scripts / ".cache" / "skip.ws",
        "generated": scripts / "generated" / "skip.ws",
    }
    files["player"].write_text(
        "class Player\n{\n    var name : string;\n    function tick() {}\n}\n",
        encoding="utf-8",
    )
    files["quest"].write_text("state QuestState {}\n", encoding="utf-8")
    files["vanilla"].write_text("class BaseCharacter {}\n", encoding="utf-8")
    files["bin"].write_text("class SkippedBin {}\n", encoding="utf-8")
    files["cache"].write_text("class SkippedCache {}\n", encoding="utf-8")
    files["generated"].write_text("class SkippedGenerated {}\n", encoding="utf-8")
    (root / "witcherscript.toml").write_text(
        """
[project]
name = "WorkspaceFixture"

[redkit]
game_directory = "game"

[scripts]
source_roots = ["scripts"]
vanilla_roots = ["vanilla/scripts"]
exclude = ["**/bin/**", "**/.cache/**", "**/generated/**"]
""".lstrip(),
        encoding="utf-8",
    )
    return files
