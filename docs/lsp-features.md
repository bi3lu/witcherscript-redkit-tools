# Language Server Features

The WitcherScript language server exposes standard Language Server Protocol features for `.ws` files. It maintains an in-memory document cache, reads workspace configuration, indexes project files, and serves editor requests from the project symbol table.

## Lifecycle

Supported lifecycle messages:

- `initialize`
- `initialized`
- `shutdown`
- `exit`

During `initialize`, the server stores the workspace root URI, loads `witcherscript.toml`, scans configured script roots, and builds the project index.

## Document Synchronization

Supported synchronization messages:

- `textDocument/didOpen`
- `textDocument/didChange`
- `textDocument/didSave`
- `workspace/didChangeWatchedFiles`

The server uses full-document synchronization. Opened and changed files update the document cache and the project index. Watched file changes refresh or remove indexed files when the LSP client reports external changes.

## Workspace Commands

Supported request:

- `workspace/executeCommand`

Supported command:

- `witcherscript.refreshIndex`

This command reloads `witcherscript.toml`, rebuilds the project index, and keeps open document contents active in the rebuilt index. It is intended for clients that run REDkit tooling commands, such as `ws-redkit init`, while the language server process is already running.

## Diagnostics

Supported publication:

- `textDocument/publishDiagnostics`

Diagnostics are generated from the lexer and parser. The server reports syntax errors with stable codes and LSP ranges.

Examples:

- `WS1000`: unexpected character
- `WS1001`: unexpected token
- `WS1002`: unterminated string literal
- `WS1003`: unterminated block comment
- `WS2001`: expected semicolon
- `WS2002`: expected closing brace

## Document Symbols

Supported request:

- `textDocument/documentSymbol`

The server returns hierarchical document symbols for editor outlines. Indexed declarations include classes, states, functions, events, fields, and local declarations where relevant to the current symbol tree.

Example outline:

```text
Player
  title
  make
```

## Workspace Symbols

Supported request:

- `workspace/symbol`

The server searches indexed project symbols with case-insensitive substring matching. Results include classes, states, functions, events, and fields.

## Go To Definition

Supported request:

- `textDocument/definition`

The server resolves the identifier under the cursor against the project symbol table. Local declarations in the current file are preferred over symbols from other files when names overlap.

## Completion

Supported request:

- `textDocument/completion`

Completion items include:

- WitcherScript keywords
- symbols from the current file
- global project symbols

Completion item kinds are mapped to LSP classes, functions, fields, variables, events, and keywords.

## Hover

Supported request:

- `textDocument/hover`

Hover displays the resolved symbol signature, kind, container, and file URI. The response uses Markdown content.

## References

Supported request:

- `textDocument/references`

References are resolved by exact identifier matching across indexed files. The lookup respects word boundaries and can include or exclude the declaration based on the request context.

## Workspace Configuration

The language server reads `witcherscript.toml` from the workspace root.

```toml
[project]
name = "MyRedkitMod"

[scripts]
source_roots = ["scripts", "content/scripts"]
vanilla_roots = ["D:/Steam/steamapps/common/The Witcher 3/content/content0/scripts"]
exclude = ["**/bin/**", "**/.cache/**", "**/.ws-cache/**", "**/generated/**"]
```

If the file is absent, the workspace root is used as the script root.
