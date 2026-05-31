# VS Code Extension

The VS Code extension under `src/vscode` is a lightweight client for exercising the WitcherScript language server in a real editor. It is intentionally small: the language behavior stays in the Python LSP, while REDkit project operations stay in the C# CLI.

## Capabilities

- Activates for `.ws` files through the `witcherscript` language id.
- Starts the Python language server over standard input and output.
- Watches `.ws` files and `witcherscript.toml` for workspace changes.
- Shows LSP status in the VS Code status bar.
- Exposes `WitcherScript: Show Output Logs`.
- Exposes `WitcherScript: Refresh Project Index`.
- Exposes `WitcherScript: Initialize REDkit Config`.
- Exposes `WitcherScript: Recompile Scripts`.
- Exposes `WitcherScript: Launch Game`.
- Exposes `WitcherScript: Restart Language Server`.
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
  "witcherscript.workspace.root": "${workspaceFolder}",
  "witcherscript.languageServer.path": "",
  "witcherscript.languageServer.command": "uv",
  "witcherscript.languageServer.args": ["run", "witcherscript-lsp"],
  "witcherscript.languageServer.cwd": "${extensionPath}/../.."
}
```

Use absolute paths, `${extensionPath}`, or `${workspaceFolder}` when testing against projects outside this repository.

Set `witcherscript.languageServer.path` to a concrete executable when you do not want to rely on `uv` from `PATH`. For example:

```json
{
  "witcherscript.languageServer.path": "/absolute/path/to/.venv/bin/witcherscript-lsp",
  "witcherscript.languageServer.args": []
}
```

The status bar item opens the WitcherScript output channel. Startup failures also offer actions for opening logs or the language server settings.

## Daily Debugging Workflow

1. Open `src/vscode` in VS Code.
2. Run `npm install` and `npm run compile`.
3. Start `Run WitcherScript Extension`.
4. Use the debug host status bar item to inspect LSP state.
5. Run `WitcherScript: Restart Language Server` after Python or configuration changes.
6. Run `WitcherScript: Refresh Project Index` after external file changes.

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
If `witcherscript.toml` already exists, the extension asks before calling `init --force`.

Script recompilation requires an executable configured for the REDkit workflow:

```json
{
  "witcherscript.redkit.recompile.executable": "D:/Tools/recompile.exe"
}
```

Game launch can either use the executable resolved by the C# CLI from `witcherscript.toml` or an explicit override:

```json
{
  "witcherscript.redkit.launch.executable": "D:/Steam/steamapps/common/The Witcher 3/bin/x64_dx12/witcher3.exe",
  "witcherscript.redkit.launch.args": ["-debugscripts"]
}
```
