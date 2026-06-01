# Architecture

WitcherScript REDkit Tools is organized around reusable language and project components. The editor-facing surface is the WitcherScript language server. REDkit-specific data is modeled separately in the C# tooling project.

```text
LSP client
    |
WitcherScript Language Server
    |
Workspace configuration
    |
Lexer + parser + diagnostics
    |
File index + symbol table + project index
```

```text
REDkit tooling CLI
    |
REDkit project model
    |
Content repositories + script roots
    |
Game / REDkit / project directories
```

## Python Language Server

The Python package under `src/py/witcherscript_langserver` owns language intelligence for `.ws` files.

Core responsibilities:

- LSP request and notification handling
- document cache management
- `witcherscript.toml` loading
- workspace scanning
- lexing and parsing
- syntax diagnostics
- file-level indexes
- project-level symbol tables
- document symbols
- workspace symbols
- completion
- hover
- go to definition
- simple references

Important modules:

- `lsp/server.py`: LSP server construction, feature registration, and workspace commands
- `workspace/workspace.py`: workspace state, URI normalization, file indexing updates
- `workspace/config.py`: `witcherscript.toml` model and loader
- `parser/lexer.py`: tokenization
- `parser/parser.py`: tolerant structural parser
- `diagnostics.py`: conversion from parser diagnostics to LSP diagnostics
- `indexing/file_index.py`: AST, symbols, scopes, imports, and diagnostics for one file
- `indexing/project_index.py`: project-wide file index
- `analysis/symbol_table.py`: symbol, scope, and type-reference model
- `analysis/inheritance.py`: class inheritance lookup
- `completion.py`, `definition.py`, `hover.py`, `references.py`, `symbols.py`: LSP feature providers

## VS Code Extension

The VS Code extension under `src/vscode` is a thin client around the language
server and REDkit CLI. It owns editor activation, command registration, status
UI, output logs, and user-facing setup diagnostics.

Important modules:

- `extension.ts`: activation, command registration, and dependency wiring
- `languageServer.ts`: LSP lifecycle, restart, startup errors, and index refresh
- `redkitCommands.ts`: REDkit config initialization, recompile, and game launch
- `setupDoctor.ts`: setup checklist for modders and developers
- `configuration.ts`: VS Code settings mapped to command-line models
- `paths.ts`: workspace, path expansion, file checks, and lightweight TOML helpers
- `statusBar.ts`: status bar presentation
- `process.ts`: child process helper used by setup checks

## C# REDkit Tooling

The .NET solution under `src/dotnet` owns REDkit-oriented project data and CLI integration.

Current responsibilities:

- REDkit project data model
- content repository model
- project, game, and REDkit directory detection
- `witcherscript.toml` generation
- project validation
- script recompilation and game launch process adapters
- command-line entry point
- .NET build and test integration

Important projects:

- `WitcherScript.RedkitTooling`: library with project and repository models
- `WitcherScript.RedkitTooling.Cli`: command-line executable
- `WitcherScript.RedkitTooling.Tests`: xUnit tests for the tooling library

## Workspace Lifecycle

1. The LSP client starts `witcherscript-lsp`.
2. The client sends `initialize` with a workspace root URI.
3. The server loads `witcherscript.toml` from that root when present.
4. The server resolves configured script roots and exclude rules.
5. The server scans `.ws` files, parses them, and builds the project index.
6. Open, change, save, and watched-file notifications update the index.
7. LSP feature requests read from the document cache and symbol table.

When the REDkit CLI creates or updates `witcherscript.toml`, the client can call
`workspace/executeCommand` with `witcherscript.refreshIndex`. The server reloads
the workspace configuration, rebuilds the project index, and reapplies open
documents from the in-memory cache.

## Indexing Model

The indexing layer is split into per-file and project-wide structures.

`FileIndex` stores:

- local path and LSP URI
- parsed module
- imports
- symbols
- scopes
- type references
- syntax diagnostics

`ProjectIndex` stores:

- all indexed files
- global symbol table
- inheritance index
- import lookup
- project diagnostics aggregated from files

The symbol table tracks declarations with the following kinds:

- class
- event
- field
- function
- local
- state

## Diagnostics Flow

```text
source text
    |
lexer
    |
parser
    |
SyntaxDiagnostic
    |
LSP Diagnostic
    |
textDocument/publishDiagnostics
```

Diagnostics use stable WitcherScript codes such as `WS1002`, `WS2001`, and `WS2002`, and are deduplicated before publication.
