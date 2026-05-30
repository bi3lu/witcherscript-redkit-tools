# WitcherScript REDkit Tools for VS Code

VS Code harness for testing the WitcherScript language server and REDkit project tooling.

## Features

- Activates for `.ws` files.
- Starts the Python language server through a configurable local command.
- Registers `WitcherScript: Refresh Project Index`.
- Registers `WitcherScript: Initialize REDkit Config`.
- Provides a debug launch configuration for Extension Host development.

## Development

Install extension dependencies:

```bash
npm install
```

Compile the extension:

```bash
npm run compile
```

Open this folder in VS Code and run `Run WitcherScript Extension` from the debugger. The debug configuration opens `samples/minimal_project` as the test workspace.

## Settings

```json
{
  "witcherscript.languageServer.command": "uv",
  "witcherscript.languageServer.args": ["run", "witcherscript-lsp"],
  "witcherscript.languageServer.cwd": "${extensionPath}/../..",
  "witcherscript.redkit.command": "dotnet",
  "witcherscript.redkit.args": []
}
```

When `witcherscript.redkit.args` is empty, the extension runs the repository-local C# CLI project through `dotnet run`.
