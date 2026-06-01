"""Code action provider for safe WitcherScript quick fixes."""

from __future__ import annotations

from difflib import get_close_matches

from lsprotocol import types

from witcherscript_langserver.analysis.symbol_table import SymbolKind
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.workspace.config import CONFIG_FILE_NAME

from .lsp_utils import word_range_at_position


def code_actions(
    index: ProjectIndex,
    source: str,
    uri: str,
    params: types.CodeActionParams,
    config_uri: str | None,
) -> list[types.CodeAction]:
    """Build code actions for a document range and diagnostics.

    Args:
        index: Project index.
        source: Current document text.
        uri: Current document URI.
        params: LSP code action request parameters.
        config_uri: Workspace configuration URI, when known.

    Returns:
        Safe quick fixes and navigation actions.
    """
    actions: list[types.CodeAction] = []

    if config_uri is None:
        actions.append(_initialize_config_action())

    for diagnostic in params.context.diagnostics:
        code = str(diagnostic.code)

        if code == "WS2001":
            actions.append(
                _insert_text_action("Add missing semicolon", uri, diagnostic.range.end, ";")
            )

        elif code == "WS2002":
            actions.append(
                _insert_text_action(
                    "Add missing closing brace",
                    uri,
                    diagnostic.range.end,
                    "\n}",
                )
            )

        elif code in {"WS3002", "WS3003", "WS3004"}:
            suggestion = _closest_symbol_name(index, diagnostic.message)
            word_range = word_range_at_position(source, diagnostic.range.start)

            if suggestion is not None and word_range is not None:
                actions.append(
                    _replace_range_action(
                        f"Change to '{suggestion}'",
                        uri,
                        word_range,
                        suggestion,
                    )
                )

        elif code.startswith("WS400") and config_uri is not None:
            actions.append(_open_config_action(config_uri))

    return _deduplicate_actions(actions)


def _closest_symbol_name(index: ProjectIndex, message: str) -> str | None:
    quoted = _first_quoted_value(message)

    if quoted is None:
        return None

    names = sorted(
        {
            symbol.name
            for symbol in index.symbols
            if symbol.kind
            in {
                SymbolKind.CLASS,
                SymbolKind.EVENT,
                SymbolKind.FIELD,
                SymbolKind.FUNCTION,
                SymbolKind.LOCAL,
                SymbolKind.STATE,
            }
        }
    )
    matches = get_close_matches(quoted, names, n=1, cutoff=0.72)
    return matches[0] if matches else None


def _first_quoted_value(message: str) -> str | None:
    start = message.find("'")

    if start == -1:
        return None

    end = message.find("'", start + 1)

    if end == -1:
        return None

    return message[start + 1 : end]


def _insert_text_action(
    title: str,
    uri: str,
    position: types.Position,
    text: str,
) -> types.CodeAction:
    return types.CodeAction(
        title=title,
        kind=types.CodeActionKind.QuickFix,
        edit=types.WorkspaceEdit(
            changes={
                uri: [
                    types.TextEdit(
                        range=types.Range(start=position, end=position),
                        new_text=text,
                    )
                ]
            }
        ),
    )


def _replace_range_action(
    title: str,
    uri: str,
    range_: types.Range,
    text: str,
) -> types.CodeAction:
    return types.CodeAction(
        title=title,
        kind=types.CodeActionKind.QuickFix,
        edit=types.WorkspaceEdit(
            changes={
                uri: [
                    types.TextEdit(
                        range=range_,
                        new_text=text,
                    )
                ]
            }
        ),
    )


def _initialize_config_action() -> types.CodeAction:
    return types.CodeAction(
        title=f"Create {CONFIG_FILE_NAME}",
        kind=types.CodeActionKind.QuickFix,
        command=types.Command(
            title=f"Create {CONFIG_FILE_NAME}",
            command="witcherscript.redkitInit",
        ),
    )


def _open_config_action(config_uri: str) -> types.CodeAction:
    return types.CodeAction(
        title=f"Open {CONFIG_FILE_NAME}",
        kind=types.CodeActionKind.QuickFix,
        command=types.Command(
            title=f"Open {CONFIG_FILE_NAME}",
            command="vscode.open",
            arguments=[config_uri],
        ),
    )


def _deduplicate_actions(actions: list[types.CodeAction]) -> list[types.CodeAction]:
    seen: set[str] = set()
    deduplicated: list[types.CodeAction] = []

    for action in actions:
        if action.title in seen:
            continue

        seen.add(action.title)
        deduplicated.append(action)

    return deduplicated
