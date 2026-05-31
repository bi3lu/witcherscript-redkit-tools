# Changelog

All notable changes to WitcherScript REDkit Tools are documented in this file.

## 0.3.0 - Context-Aware Language Intelligence

- Added scope-aware name resolution for globals, classes, functions, locals, and parameters.
- Added context-aware completion for types, inheritance clauses, locals, parameters, members, and imports.
- Added expression AST support for calls, member access, assignments, binary expressions, unary expressions, and array access.
- Added type and member lookup for richer hover, definition, completion, and diagnostics.
- Added signature help for function calls.
- Expanded semantic diagnostics for unknown members, argument validation, assignment mismatches, return mismatches, duplicate classes, unresolved imports, and invalid inheritance.
- Added corpus analysis tooling and fixture coverage for real-world WitcherScript samples.
- Improved the VS Code extension with status feedback, output logs, restart support, REDkit recompile, and game launch commands.
- Improved REDkit CLI validation, config initialization, Windows detection, and recompile log parsing.
- Added LSP diagnostics for invalid or broken `witcherscript.toml`.

## 0.2.0 - Language Server and Project Tooling

- Added the initial usable Language Server Protocol implementation.
- Added workspace indexing through `witcherscript.toml`.
- Added diagnostics, document symbols, workspace symbols, completion, hover, definition, and references.
- Added REDkit project tooling integration between the Python language server and the C# CLI.
- Added the VS Code extension harness for local editor testing.
- Added end-to-end language-server fixtures and CI checks for the VS Code extension.

## 0.1.0 - WitcherScript Language Core Foundation

- Added the initial repository structure for Python and .NET development.
- Added Python packaging and dependency management with `uv`.
- Added .NET solution structure and GitHub Actions CI.
- Implemented the WitcherScript lexer and tolerant structural parser.
- Added AST output through the developer CLI.
- Added lexer and parser tests with snapshots.
- Added baseline REDkit project model types in C#.
