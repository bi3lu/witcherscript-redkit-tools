"""Tests for semantic token classification."""

from pathlib import Path

from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.lsp.semantic_tokens import (
    TOKEN_MODIFIERS,
    TOKEN_TYPES,
    semantic_tokens,
)
from witcherscript_langserver.workspace.config import load_workspace_config


def test_semantic_tokens_classify_witcherscript_symbols(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    source = """
native class Player extends Base
{
    var title : string;
    var deprecatedField : int;

    native event OnSpawn(other : Base);

    function make(other : Base) : Base
    {
        var local : Base;
        local.merge(1, 2);
        return other;
    }
}
""".lstrip()
    player = scripts / "player.ws"
    player.write_text(source, encoding="utf-8")
    (scripts / "base.ws").write_text(
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
    (tmp_path / "witcherscript.toml").write_text(
        '[scripts]\nsource_roots = ["scripts"]\n',
        encoding="utf-8",
    )
    index = ProjectIndex.build(load_workspace_config(tmp_path))

    decoded = _decode(source, semantic_tokens(index, player.as_uri()).data)

    assert ("Player", "class", {"declaration", "native"}) in decoded
    assert ("title", "property", {"declaration"}) in decoded
    assert ("deprecatedField", "property", {"declaration", "deprecated"}) in decoded
    assert ("OnSpawn", "event", {"declaration", "native"}) in decoded
    assert ("make", "method", {"declaration"}) in decoded
    assert ("other", "parameter", {"declaration"}) in decoded
    assert ("local", "variable", {"declaration"}) in decoded
    assert ("Base", "type", set()) in decoded
    assert ("string", "type", {"defaultLibrary"}) in decoded
    assert ("int", "type", {"defaultLibrary"}) in decoded


def _decode(source: str, data: list[int]) -> list[tuple[str, str, set[str]]]:
    decoded: list[tuple[str, str, set[str]]] = []
    line = 0
    character = 0

    for index in range(0, len(data), 5):
        delta_line, delta_start, length, token_type_index, modifier_mask = data[index : index + 5]
        line += delta_line
        character = delta_start if delta_line else character + delta_start
        lexeme = _lexeme_at(source, line, character, length)
        token_type = TOKEN_TYPES[token_type_index]
        modifiers = {
            modifier for bit, modifier in enumerate(TOKEN_MODIFIERS) if modifier_mask & (1 << bit)
        }
        decoded.append((lexeme, token_type, modifiers))

    return decoded


def _lexeme_at(source: str, line: int, character: int, length: int) -> str:
    lines = source.splitlines()
    return lines[line][character : character + length]
