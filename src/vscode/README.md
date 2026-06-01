# WitcherScript REDkit Tools for VS Code

VS Code extension for editing WitcherScript projects used with The Witcher 3
REDkit. It connects VS Code to the Python language server and .NET REDkit CLI,
then exposes the workflow through editor commands.

## For Modders

Install the `.vsix`, open your mod workspace, and run:

```text
WitcherScript: Doctor Setup
```

The doctor report checks `uv`, .NET SDK, `witcherscript.toml`, REDkit paths,
vanilla script roots, LSP state, and REDkit CLI availability. Use it whenever
the extension does not start cleanly or a REDkit command fails.

## Features

- Activates for `.ws` files.
- Starts the WitcherScript language server through a configurable command.
- Provides diagnostics, completion, hover, definition, references, signature
  help, rename, implementations, symbols, and semantic highlighting.
- Shows WitcherScript LSP status in the status bar.
- Registers `WitcherScript: Doctor Setup`.
- Registers `WitcherScript: Show Output Logs`.
- Registers `WitcherScript: Refresh Project Index`.
- Registers `WitcherScript: Initialize REDkit Config`.
- Registers `WitcherScript: Recompile Scripts`.
- Registers `WitcherScript: Launch Game`.
- Registers `WitcherScript: Restart Language Server`.

## Settings

```json
{
  "witcherscript.workspace.root": "${workspaceFolder}",
  "witcherscript.languageServer.path": "",
  "witcherscript.languageServer.command": "uv",
  "witcherscript.languageServer.args": ["run", "witcherscript-lsp"],
  "witcherscript.languageServer.cwd": "",
  "witcherscript.redkit.command": "dotnet",
  "witcherscript.redkit.args": []
}
```

When `witcherscript.languageServer.cwd` is empty, packaged `.vsix` builds run
the bundled language server from the extension install directory. Local
development falls back to the repository root.

When `witcherscript.redkit.args` is empty, packaged `.vsix` builds run the
bundled C# CLI source through `dotnet run`. Local development falls back to the
repository-local C# CLI project.

## Development

```bash
npm ci --prefer-online
npm run smoke
```

Open this folder in VS Code and run `Run WitcherScript Extension` from the
debugger. The debug configuration opens `samples/minimal_project` as the test
workspace.

## Packaging

Build a local `.vsix` from the repository root:

```bash
uv run python scripts/prepare_vscode_package.py
npm --prefix src/vscode run package:vsix -- --out ../../dist/witcherscript-redkit-tools.vsix
```
