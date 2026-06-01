"""Semantic token provider for WitcherScript source files."""

from __future__ import annotations

from dataclasses import dataclass

from lsprotocol import types

from witcherscript_langserver.analysis.diagnostics_rules import BUILTIN_TYPES
from witcherscript_langserver.analysis.name_resolution import NameResolver
from witcherscript_langserver.analysis.symbol_table import Symbol, SymbolKind
from witcherscript_langserver.indexing.file_index import FileIndex
from witcherscript_langserver.indexing.project_index import ProjectIndex
from witcherscript_langserver.parser.ast import ClassDecl, Decl, FunctionDecl, StateDecl, VarDecl
from witcherscript_langserver.parser.lexer import tokenize
from witcherscript_langserver.parser.tokens import SourceRange, Token, TokenKind

TOKEN_TYPES = (
    types.SemanticTokenTypes.Class.value,
    types.SemanticTokenTypes.Function.value,
    types.SemanticTokenTypes.Method.value,
    types.SemanticTokenTypes.Property.value,
    types.SemanticTokenTypes.Variable.value,
    types.SemanticTokenTypes.Parameter.value,
    types.SemanticTokenTypes.Type.value,
    "event",
)
TOKEN_MODIFIERS = (
    types.SemanticTokenModifiers.Declaration.value,
    types.SemanticTokenModifiers.DefaultLibrary.value,
    types.SemanticTokenModifiers.Deprecated.value,
    "native",
)
SEMANTIC_TOKENS_LEGEND = types.SemanticTokensLegend(
    token_types=TOKEN_TYPES,
    token_modifiers=TOKEN_MODIFIERS,
)


@dataclass(frozen=True)
class SemanticToken:
    """Internal semantic token representation.

    Attributes:
        line: Zero-based token line.
        character: Zero-based token start character.
        length: Token length in UTF-16 code units. WitcherScript identifiers are
            treated as ASCII-compatible here, so Python string length is enough.
        token_type: Semantic token type name.
        modifiers: Semantic token modifier names.
        priority: Priority used when duplicate ranges are produced.
    """

    line: int
    character: int
    length: int
    token_type: str
    modifiers: frozenset[str]
    priority: int


def semantic_tokens(index: ProjectIndex, uri: str) -> types.SemanticTokens:
    """Build full-document semantic tokens for an indexed file.

    Args:
        index: Project index.
        uri: LSP document URI.

    Returns:
        Encoded LSP semantic tokens.
    """
    file_index = _file_index(index, uri)

    if file_index is None:
        return types.SemanticTokens(data=[])

    lexer_result = tokenize(file_index.source)
    tokens = [token for token in lexer_result.tokens if token.kind != TokenKind.EOF]
    semantic = [
        *_declaration_tokens(file_index, tokens),
        *_type_tokens(file_index, tokens),
        *_reference_tokens(index, file_index, tokens),
    ]
    return types.SemanticTokens(data=_encode_tokens(_deduplicate(semantic)))


def _file_index(index: ProjectIndex, uri: str) -> FileIndex | None:
    for file_index in index.files.values():
        if file_index.uri == uri:
            return file_index

    return None


def _declaration_tokens(file_index: FileIndex, tokens: list[Token]) -> list[SemanticToken]:
    semantic: list[SemanticToken] = []

    for symbol in file_index.symbols:
        token = _symbol_name_token(symbol, tokens)

        if token is None:
            continue

        modifiers = {
            "declaration",
            *_symbol_metadata_modifiers(file_index.module.declarations, symbol),
        }
        semantic.append(_semantic_token(token, _symbol_token_type(symbol), modifiers, priority=100))

    for declaration in _function_declarations(file_index.module.declarations):
        for param in declaration.params:
            token = _first_identifier_token(tokens, param.name, param.range)

            if token is not None:
                semantic.append(
                    _semantic_token(
                        token, types.SemanticTokenTypes.Parameter.value, {"declaration"}, 110
                    )
                )

    return semantic


def _type_tokens(file_index: FileIndex, tokens: list[Token]) -> list[SemanticToken]:
    semantic: list[SemanticToken] = []

    for token in tokens:
        if token.kind != TokenKind.IDENTIFIER:
            continue

        if token.lexeme in BUILTIN_TYPES:
            semantic.append(
                _semantic_token(
                    token,
                    types.SemanticTokenTypes.Type.value,
                    {types.SemanticTokenModifiers.DefaultLibrary.value},
                    priority=80,
                )
            )
            continue

        for reference in file_index.type_references:
            if token.lexeme == reference.name and _range_contains(reference.range, token.range):
                semantic.append(
                    _semantic_token(token, types.SemanticTokenTypes.Type.value, set(), 70)
                )
                break

    return semantic


def _reference_tokens(
    index: ProjectIndex, file_index: FileIndex, tokens: list[Token]
) -> list[SemanticToken]:
    semantic: list[SemanticToken] = []
    resolver = NameResolver(index)
    param_ranges = set(_param_ranges(file_index.module.declarations))

    for token in tokens:
        if token.kind != TokenKind.IDENTIFIER or token.lexeme in BUILTIN_TYPES:
            continue

        result = resolver.resolve(file_index.uri, token.range.start.offset, token.lexeme)
        if result is None:
            continue

        symbol = result.symbol
        modifiers = set(_symbol_metadata_modifiers(file_index.module.declarations, symbol))
        token_type = _symbol_token_type(symbol)

        if symbol.kind == SymbolKind.LOCAL and _range_key(symbol.range) in param_ranges:
            token_type = types.SemanticTokenTypes.Parameter.value

        semantic.append(_semantic_token(token, token_type, modifiers, priority=30))

    return semantic


def _symbol_name_token(symbol: Symbol, tokens: list[Token]) -> Token | None:
    return _first_identifier_token(tokens, symbol.name, symbol.range)


def _first_identifier_token(tokens: list[Token], name: str, range_: SourceRange) -> Token | None:
    for token in tokens:
        if (
            token.kind == TokenKind.IDENTIFIER
            and token.lexeme == name
            and _range_contains(range_, token.range)
        ):
            return token

    return None


def _symbol_token_type(symbol: Symbol) -> str:
    if symbol.kind == SymbolKind.CLASS:
        return types.SemanticTokenTypes.Class.value

    if symbol.kind == SymbolKind.EVENT:
        return "event"

    if symbol.kind == SymbolKind.FIELD:
        return types.SemanticTokenTypes.Property.value

    if symbol.kind == SymbolKind.FUNCTION:
        if symbol.container_name is not None:
            return types.SemanticTokenTypes.Method.value

        return types.SemanticTokenTypes.Function.value

    if symbol.kind == SymbolKind.LOCAL:
        return types.SemanticTokenTypes.Variable.value

    if symbol.kind == SymbolKind.STATE:
        return types.SemanticTokenTypes.Class.value

    return types.SemanticTokenTypes.Variable.value


def _symbol_metadata_modifiers(declarations: list[Decl], symbol: Symbol) -> frozenset[str]:
    flags = _flags_for_symbol(declarations, symbol)
    modifiers: set[str] = set()

    if "native" in flags:
        modifiers.add("native")

    if "deprecated" in flags or "deprecated" in symbol.name.lower():
        modifiers.add(types.SemanticTokenModifiers.Deprecated.value)

    return frozenset(modifiers)


def _flags_for_symbol(declarations: list[Decl], symbol: Symbol) -> frozenset[str]:
    for declaration in declarations:
        flags = _declaration_flags_for_symbol(declaration, symbol, container_name=None)

        if flags is not None:
            return flags

    return frozenset()


def _declaration_flags_for_symbol(
    declaration: Decl,
    symbol: Symbol,
    container_name: str | None,
) -> frozenset[str] | None:
    if isinstance(declaration, ClassDecl):
        if _matches_symbol(symbol, declaration.name, SymbolKind.CLASS, container_name):
            return frozenset(declaration.flags)

        return _member_flags(declaration.members, symbol, declaration.name)

    if isinstance(declaration, StateDecl):
        if _matches_symbol(symbol, declaration.name, SymbolKind.STATE, container_name):
            return frozenset()

        return _member_flags(declaration.members, symbol, declaration.name)

    if isinstance(declaration, FunctionDecl):
        kind = SymbolKind.EVENT if "event" in declaration.flags else SymbolKind.FUNCTION

        if _matches_symbol(symbol, declaration.name, kind, container_name):
            return frozenset(declaration.flags)

        for param in declaration.params:
            if _matches_symbol(symbol, param.name, SymbolKind.LOCAL, declaration.name):
                return frozenset(param.flags)

        for local in declaration.locals:
            if _matches_symbol(symbol, local.name, SymbolKind.LOCAL, declaration.name):
                return frozenset(local.flags)

        return None

    if isinstance(declaration, VarDecl) and _matches_symbol(
        symbol,
        declaration.name,
        SymbolKind.FIELD,
        container_name,
    ):
        return frozenset(declaration.flags)

    return None


def _member_flags(
    members: list[Decl],
    symbol: Symbol,
    container_name: str,
) -> frozenset[str] | None:
    for member in members:
        flags = _declaration_flags_for_symbol(member, symbol, container_name)

        if flags is not None:
            return flags

    return None


def _matches_symbol(
    symbol: Symbol,
    name: str,
    kind: SymbolKind,
    container_name: str | None,
) -> bool:
    return symbol.name == name and symbol.kind == kind and symbol.container_name == container_name


def _function_declarations(declarations: list[Decl]) -> list[FunctionDecl]:
    functions: list[FunctionDecl] = []

    for declaration in declarations:
        if isinstance(declaration, FunctionDecl):
            functions.append(declaration)

        elif isinstance(declaration, ClassDecl | StateDecl):
            functions.extend(_function_declarations(declaration.members))

    return functions


def _param_ranges(declarations: list[Decl]) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []

    for declaration in declarations:
        if isinstance(declaration, FunctionDecl):
            ranges.extend(_range_key(param.range) for param in declaration.params)

        elif isinstance(declaration, ClassDecl | StateDecl):
            ranges.extend(_param_ranges(declaration.members))

    return ranges


def _range_key(range_: SourceRange) -> tuple[int, int]:
    return (range_.start.offset, range_.end.offset)


def _range_contains(outer: SourceRange, inner: SourceRange) -> bool:
    return outer.start.offset <= inner.start.offset and inner.end.offset <= outer.end.offset


def _semantic_token(
    token: Token,
    token_type: str,
    modifiers: set[str] | frozenset[str],
    priority: int,
) -> SemanticToken:
    return SemanticToken(
        line=token.range.start.line,
        character=token.range.start.character,
        length=len(token.lexeme),
        token_type=token_type,
        modifiers=frozenset(modifiers),
        priority=priority,
    )


def _deduplicate(tokens: list[SemanticToken]) -> list[SemanticToken]:
    by_range: dict[tuple[int, int, int], SemanticToken] = {}

    for token in tokens:
        key = (token.line, token.character, token.length)
        current = by_range.get(key)

        if current is None or token.priority > current.priority:
            by_range[key] = token

    return sorted(by_range.values(), key=lambda token: (token.line, token.character))


def _encode_tokens(tokens: list[SemanticToken]) -> list[int]:
    data: list[int] = []
    previous_line = 0
    previous_character = 0

    for token in tokens:
        delta_line = token.line - previous_line
        delta_start = token.character if delta_line != 0 else token.character - previous_character
        data.extend(
            [
                delta_line,
                delta_start,
                token.length,
                TOKEN_TYPES.index(token.token_type),
                _modifier_mask(token.modifiers),
            ]
        )
        previous_line = token.line
        previous_character = token.character

    return data


def _modifier_mask(modifiers: frozenset[str]) -> int:
    mask = 0

    for modifier in modifiers:
        if modifier in TOKEN_MODIFIERS:
            mask |= 1 << TOKEN_MODIFIERS.index(modifier)

    return mask
