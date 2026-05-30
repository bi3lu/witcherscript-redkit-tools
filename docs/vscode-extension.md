# VS Code Extension

The VS Code extension under `src/vscode` is a lightweight client for exercising the WitcherScript language server in a real editor. It is intentionally small: the language behavior stays in the Python LSP, while REDkit project operations stay in the C# CLI.

## Capabilities

- Activates for `.ws` files through the `witcherscript` language id.
- Starts the Python language server over standard input and output.
- Watches `.ws` files and `witcherscript.toml` for workspace changes.
- Exposes `WitcherScript: Refresh Project Index`.
- Exposes `WitcherScript: Initialize REDkit Config`.
- Provides Extension Host debug configuration.

## Local Setup

Install dependencies from the extension directory:

```bash
cd src/vscode
npm install
npm run compile
```

Open `src/vscode` in VS Code and run the `Run WitcherScript Extension` launch configuration. The debug host opens `samples/minimal_project`, which contains a sample `witcherscript.toml` and `.ws` file.

## Language Server Settings

The extension starts the server with these defaults:

```json
{
  "witcherscript.languageServer.command": "uv",
  "witcherscript.languageServer.args": ["run", "witcherscript-lsp"],
  "witcherscript.languageServer.cwd": "${extensionPath}/../.."
}
```

Use absolute paths, `${extensionPath}`, or `${workspaceFolder}` when testing against projects outside this repository.

## REDkit Tooling Settings

By default, `WitcherScript: Initialize REDkit Config` runs the repository-local C# CLI project:

```bash
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- init --project-dir <workspace>
```

Override the command when using a packaged CLI:

```json
{
  "witcherscript.redkit.command": "ws-redkit",
  "witcherscript.redkit.args": []
}
```

The command refreshes the LSP project index after `witcherscript.toml` is generated.
