"""Tests for project symbol, scope, inheritance, and import indexing."""

from pathlib import Path

from witcherscript_langserver.analysis.symbol_table import ScopeKind, SymbolKind
from witcherscript_langserver.config import load_workspace_config
from witcherscript_langserver.indexing.project_index import ProjectIndex


def test_symbol_table_indexes_declarations_scopes_and_type_references(tmp_path: Path) -> None:
    script = _write_symbol_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))
    table = index.symbol_table

    assert [
        (symbol.name, symbol.kind, symbol.container_name, symbol.type_name)
        for symbol in table.symbols
    ] == [
        ("Base", SymbolKind.CLASS, None, None),
        ("Derived", SymbolKind.CLASS, None, "Base"),
        ("title", SymbolKind.FIELD, "Derived", "string"),
        ("OnInit", SymbolKind.EVENT, "Derived", None),
        ("make", SymbolKind.FUNCTION, "Derived", "Derived"),
        ("other", SymbolKind.LOCAL, "make", "Base"),
        ("local", SymbolKind.LOCAL, "make", "Base"),
        ("DerivedState", SymbolKind.STATE, None, "BaseState"),
    ]
    assert table.symbols_for_file(script.as_uri()) == table.symbols
    assert [symbol.name for symbol in table.lookup("Derived")] == ["Derived"]
    base_symbol = table.lookup_type("Base")
    assert base_symbol is not None
    assert base_symbol.name == "Base"
    assert [symbol.name for symbol in table.global_symbols()] == [
        "Base",
        "Derived",
        "DerivedState",
    ]
    assert all(symbol.selection_range == symbol.range for symbol in table.symbols)

    assert [(scope.name, scope.kind, scope.parent_name) for scope in table.scopes] == [
        ("<global>", ScopeKind.GLOBAL, None),
        ("Base", ScopeKind.CLASS, "<global>"),
        ("Derived", ScopeKind.CLASS, "<global>"),
        ("OnInit", ScopeKind.FUNCTION, "Derived"),
        ("make", ScopeKind.FUNCTION, "Derived"),
        ("DerivedState", ScopeKind.STATE, "<global>"),
    ]
    assert [(reference.name, reference.container_name) for reference in table.type_references] == [
        ("Base", None),
        ("string", "Derived"),
        ("Derived", "Derived"),
        ("Base", "make"),
        ("Base", "make"),
        ("BaseState", None),
    ]


def test_inheritance_index_maps_base_and_derived_classes(tmp_path: Path) -> None:
    _write_symbol_workspace(tmp_path)
    index = ProjectIndex.build(load_workspace_config(tmp_path))

    assert index.inheritance_index.derived_classes("Base") == ("Derived",)
    assert index.inheritance_index.base_class("Derived") == "Base"
    assert index.inheritance_index.base_class("Base") is None


def test_project_index_collects_and_resolves_import_targets(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True)
    helper = scripts / "helpers.ws"
    main = scripts / "main.ws"
    helper.write_text("class Helper {}\n", encoding="utf-8")
    main.write_text('import "helpers.ws";\nclass UsesHelper {}\n', encoding="utf-8")
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )

    index = ProjectIndex.build(load_workspace_config(tmp_path))

    assert index.imports == ((main.as_uri(), '"helpers.ws"'),)
    assert index.resolve_import('"helpers.ws"') == index.files[helper]
    assert index.resolve_import("helpers") == index.files[helper]
    assert index.resolve_import("missing") is None


def _write_symbol_workspace(root: Path) -> Path:
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    script = scripts / "symbols.ws"
    script.write_text(
        """
class Base {}

class Derived extends Base
{
    var title : string;

    event OnInit() {}

    function make(other : Base) : Derived
    {
        var local : Base;
        return local;
    }
}

state DerivedState in BaseState {}
""".lstrip(),
        encoding="utf-8",
    )
    (root / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    return script
