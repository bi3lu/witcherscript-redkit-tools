# WitcherScript REDkit Tools

Developer tooling for WitcherScript projects used with The Witcher 3 REDkit.

The repository contains a Python language server for WitcherScript and a C# REDkit tooling foundation. The language server provides editor-facing language intelligence through the Language Server Protocol, while the C# project keeps Windows and REDkit-specific project data in a strongly typed model.

It also includes a minimal VS Code extension used as an editor client for local language-server testing.

## Capabilities

The WitcherScript language server currently supports:

- lexical and parser diagnostics for `.ws` files
- project configuration through `witcherscript.toml`
- workspace scanning with `source_roots`, `vanilla_roots`, and `exclude` rules
- per-file and project-wide symbol indexes
- document symbols for editor outlines
- workspace symbol search
- go to definition for indexed symbols
- hover text for known symbols
- keyword and project-symbol completion
- simple reference lookup across indexed files
- file watching updates through `workspace/didChangeWatchedFiles`
- explicit project-index refresh through `witcherscript.refreshIndex`

The REDkit tooling project contains:

- a typed REDkit project model
- content repository modeling
- project, game, and REDkit directory detection
- `witcherscript.toml` export for the language server
- validation of project and script paths
- command adapters for script recompilation and game launch
- .NET build and test integration

The VS Code extension contains:

- `.ws` language activation
- configurable Python language-server startup
- command to refresh the project index
- command to initialize `witcherscript.toml` through the C# CLI
- Extension Host debug configuration

## Repository Layout

```text
.
├─ docs/                         Project documentation
├─ samples/                      WitcherScript samples and workspace fixtures
├─ src/
│  ├─ py/                        Python language server and developer CLI
│  ├─ dotnet/                    C# REDkit tooling solution
│  └─ vscode/                    VS Code language-server client
├─ tests/py/                     Python tests and snapshots
├─ Dockerfile                    Development container image
├─ docker-compose.yml            Container workflow
├─ Makefile                      Common local commands
├─ pyproject.toml                Python package and tooling configuration
└─ uv.lock                       Locked Python dependencies
```

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- .NET SDK matching `global.json`
- Docker, when using the container workflow

REDkit and The Witcher 3 are Windows-native tools. The language server and tests run on macOS, Linux, and Windows; REDkit process integration runs against native Windows installations.

## Setup

Install Python dependencies:

```bash
uv sync --all-extras --dev
```

Restore the .NET solution:

```bash
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
```

Or run both through the project shortcut:

```bash
make sync
```

## Quality Checks

Run Python checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/py
uv run pytest
```

Run .NET checks:

```bash
dotnet test src/dotnet/WitcherScript.RedkitTooling.sln
```

Run the combined shortcuts:

```bash
make lint
make test
```

## Running The Language Server

Start the language server over standard input and output:

```bash
uv run witcherscript-lsp
```

The server is designed to be launched by an LSP client. It reads the workspace root from `initialize`, loads `witcherscript.toml` when present, indexes configured `.ws` files, and responds to standard LSP requests.

When REDkit tooling creates or updates `witcherscript.toml` while the server is already running, the LSP client can call `workspace/executeCommand` with `witcherscript.refreshIndex`. The server reloads the TOML file, rebuilds the project index, and keeps currently open document contents active in the index.

## VS Code Extension

The VS Code harness lives in `src/vscode`.

```bash
cd src/vscode
npm install
npm run compile
```

Open `src/vscode` in VS Code and run `Run WitcherScript Extension`. See [docs/vscode-extension.md](docs/vscode-extension.md) for settings and command details.

## Workspace Configuration

Place `witcherscript.toml` at the workspace root:

```toml
[project]
name = "MyRedkitMod"

[redkit]
game_directory = "D:/Steam/steamapps/common/The Witcher 3"
redkit_directory = "D:/Steam/steamapps/common/The Witcher 3 REDkit"
project_directory = "D:/REDkitProjects/MyMod"

[scripts]
source_roots = [
  "scripts",
  "content/scripts",
  "Mods/modMyMod/content/scripts"
]

vanilla_roots = [
  "D:/Steam/steamapps/common/The Witcher 3/content/content0/scripts"
]

exclude = [
  "**/bin/**",
  "**/.cache/**",
  "**/.ws-cache/**",
  "**/generated/**"
]
```

Relative paths are resolved from the workspace root. Absolute paths are used as written. If no config file exists, the language server uses the workspace root as the script root and applies the default exclude rules.

The same file can be generated by the REDkit CLI:

```bash
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- init --project-dir <path>
```

## Docker Workflow

Build the development image:

```bash
docker compose build dev
```

Run tests inside the container:

```bash
docker compose run --rm dev make test
```

Open an interactive shell:

```bash
docker compose run --rm dev
```

See [docs/containers.md](docs/containers.md) for details about volumes, Dev Containers, and Windows path mounts.

## Documentation

- [Architecture](docs/architecture.md)
- [Language Server Features](docs/lsp-features.md)
- [REDkit Project Model](docs/redkit-project-model.md)
- [WitcherScript Notes](docs/witcherscript-notes.md)
- [VS Code Extension](docs/vscode-extension.md)
- [Containers](docs/containers.md)

## License

This project is licensed under the terms of the repository license.
