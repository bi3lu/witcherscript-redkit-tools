# Architecture

The repository is organized around a reusable core rather than a single editor UI.

```text
VS Code / custom IDE / other LSP client
        |
WitcherScript Language Server
        |
Parser + Analyzer + Project Index
        |
REDkit project config
        |
C# REDkit Tooling CLI
        |
Game / REDkit / project folders
```

## Python

Python owns the WitcherScript language server and language intelligence:

- lexer and parser
- diagnostics
- document and workspace symbols
- completion
- hover
- go to definition
- references
- semantic tokens
- future formatting and rename support

## C#

C# owns REDkit and Windows-oriented project tooling:

- game and REDkit installation detection
- REDkit project detection
- project model and path validation
- config export for the language server
- build/recompile/launch process adapters
- future GUI or desktop shell integration
