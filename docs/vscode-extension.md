# VS Code Extension

The VS Code extension is the recommended way to use WitcherScript REDkit Tools
while editing mods. It starts the WitcherScript language server, exposes REDkit
workflow commands, keeps a visible status bar item, and provides a setup doctor
for checking local requirements.

The extension is intentionally a thin client. Language behavior stays in the
Python LSP, REDkit operations stay in the .NET CLI, and VS Code is responsible
for wiring those tools into a familiar editor workflow.

## For Modders

Install the `.vsix`, open your mod workspace, then run:

```text
WitcherScript: Doctor Setup
```

The doctor report opens in the `WitcherScript` output panel and checks the
things that most often break first-time setup:

- open workspace folder
- `witcherscript.toml`
- `uv`
- bundled Python CLI environment
- .NET SDK
- REDkit CLI command
- current LSP state
- Witcher 3 path
- REDkit path
- REDkit project path
- source roots
- vanilla script roots
- recompile executable setting

After the report is clean enough for your workflow, run:

```text
WitcherScript: Initialize REDkit Config
```

This creates or updates `witcherscript.toml`, then refreshes the language server
index.

## Editing Features

- Activates for `.ws` files.
- Starts the Python language server over standard input and output.
- Watches `.ws` files and `witcherscript.toml`.
- Shows LSP state in the status bar.
- Opens dedicated WitcherScript output logs.
- Provides diagnostics, hover, completion, definition, references, rename,
  signature help, implementations, and document/workspace symbols.
- Enables semantic highlighting for classes, functions, methods, fields, local
  variables, parameters, built-in types, events, native symbols, and deprecated
  symbols.
- Exposes REDkit config, recompile, and launch commands.

## Commands

| Command | Purpose |
| --- | --- |
| `WitcherScript: Doctor Setup` | Runs the setup checklist and opens the report |
| `WitcherScript: Initialize REDkit Config` | Creates `witcherscript.toml` using the REDkit CLI |
| `WitcherScript: Refresh Project Index` | Rebuilds the LSP project index |
| `WitcherScript: Recompile Scripts` | Runs the configured REDkit recompile executable |
| `WitcherScript: Launch Game` | Starts The Witcher 3 through the REDkit CLI workflow |
| `WitcherScript: Restart Language Server` | Stops and starts the LSP client |
| `WitcherScript: Show Output Logs` | Opens the WitcherScript output channel |

## Settings

Default language server settings:

```json
{
  "witcherscript.workspace.root": "${workspaceFolder}",
  "witcherscript.languageServer.path": "",
  "witcherscript.languageServer.command": "uv",
  "witcherscript.languageServer.args": ["run", "witcherscript-lsp"],
  "witcherscript.languageServer.cwd": ""
}
```

When `witcherscript.languageServer.cwd` is empty, packaged `.vsix` builds run
the bundled server from the extension install directory. Local extension
development falls back to the repository root.

Set `witcherscript.languageServer.path` when you want to run a concrete
executable, for example a virtualenv script or a packaged language server:

```json
{
  "witcherscript.languageServer.path": "/absolute/path/to/.venv/bin/witcherscript-lsp",
  "witcherscript.languageServer.args": []
}
```

Default REDkit settings:

```json
{
  "witcherscript.redkit.command": "dotnet",
  "witcherscript.redkit.args": []
}
```

When `witcherscript.redkit.args` is empty, packaged `.vsix` builds run the
bundled C# CLI source through `dotnet run`. If you install a standalone
`ws-redkit` executable later, configure:

```json
{
  "witcherscript.redkit.command": "ws-redkit",
  "witcherscript.redkit.args": []
}
```

Script recompilation requires an executable configured for your REDkit setup:

```json
{
  "witcherscript.redkit.recompile.executable": "D:/Tools/recompile.exe"
}
```

Game launch can use the executable resolved from `witcherscript.toml` or an
explicit override:

```json
{
  "witcherscript.redkit.launch.executable": "D:/Steam/steamapps/common/The Witcher 3/bin/x64_dx12/witcher3.exe",
  "witcherscript.redkit.launch.args": ["-debugscripts"]
}
```

## Troubleshooting

Run `WitcherScript: Doctor Setup` first. The report is designed to answer:

- Is the workspace folder correct?
- Is `witcherscript.toml` present?
- Does VS Code see `uv` and `.NET SDK`?
- Can the bundled language server environment run?
- Can the REDkit CLI command run?
- Are Witcher 3 and REDkit paths valid?
- Is the language server currently running?

Then use:

- `WitcherScript: Show Output Logs` for raw LSP and command output.
- `WitcherScript: Restart Language Server` after changing Python code,
  extension settings, or `witcherscript.toml`.
- `WitcherScript: Refresh Project Index` after external file changes.

## Extension Source Layout

The extension source is split by responsibility:

```text
src/vscode/src/
├─ extension.ts          activation and command registration
├─ languageServer.ts     LSP lifecycle, restart, and index refresh
├─ redkitCommands.ts     REDkit init, recompile, and launch commands
├─ setupDoctor.ts        setup checklist and report rendering
├─ configuration.ts      VS Code settings to command-line models
├─ paths.ts              workspace, path, and lightweight TOML helpers
├─ statusBar.ts          status bar presentation
├─ process.ts            child process helper
├─ constants.ts          command ids and config section
└─ types.ts              shared TypeScript interfaces
```

## Local Development

Install dependencies from the extension directory:

```bash
cd src/vscode
npm ci --prefer-online
npm run smoke
```

Open `src/vscode` in VS Code and run the `Run WitcherScript Extension` launch
configuration. The debug host opens `samples/minimal_project`, which contains a
sample `witcherscript.toml` and `.ws` file.

## Release Packaging

The release workflow builds a `.vsix` and uploads it to GitHub Releases. The
package includes:

- compiled VS Code extension JavaScript
- Python language server source under `server/`
- REDkit C# CLI source under `redkit/`

Build the same package locally:

```bash
uv run python scripts/prepare_vscode_package.py
npm --prefix src/vscode run package:vsix -- --out ../../dist/witcherscript-redkit-tools.vsix
```
