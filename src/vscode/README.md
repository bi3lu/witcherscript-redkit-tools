# WitcherScript REDkit Tools for VS Code

VS Code harness for testing the WitcherScript language server and REDkit project tooling.

## Features

- Activates for `.ws` files.
- Starts the Python language server through a configurable local command.
- Shows WitcherScript LSP status in the status bar.
- Registers `WitcherScript: Show Output Logs`.
- Registers `WitcherScript: Refresh Project Index`.
- Registers `WitcherScript: Initialize REDkit Config`.
- Registers `WitcherScript: Restart Language Server`.
- Provides a debug launch configuration for Extension Host development.

## Development

Install extension dependencies:

```bash
npm install
```

Compile the extension:

```bash
npm run lint
npm run check
npm run compile
```

Open this folder in VS Code and run `Run WitcherScript Extension` from the debugger. The debug configuration opens `samples/minimal_project` as the test workspace.

## Settings

```json
{
  "witcherscript.workspace.root": "${workspaceFolder}",
  "witcherscript.languageServer.path": "",
  "witcherscript.languageServer.command": "uv",
  "witcherscript.languageServer.args": ["run", "witcherscript-lsp"],
  "witcherscript.languageServer.cwd": "${extensionPath}/../..",
  "witcherscript.redkit.command": "dotnet",
  "witcherscript.redkit.args": []
}
```

Set `witcherscript.languageServer.path` when you want to run a concrete executable, for example a virtualenv script or packaged language server. Keep `witcherscript.languageServer.args` empty for direct executables that need no extra arguments.

When `witcherscript.redkit.args` is empty, the extension runs the repository-local C# CLI project through `dotnet run`.

## Daily Debugging

- Use the WitcherScript status bar item to open logs.
- Run `WitcherScript: Show Output Logs` when startup fails.
- Run `WitcherScript: Restart Language Server` after changing Python code or `witcherscript.toml`.
- Run `WitcherScript: Refresh Project Index` after changing files outside VS Code.
