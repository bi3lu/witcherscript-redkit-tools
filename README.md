# WitcherScript REDkit Tools

[![CI](https://github.com/bi3lu/witcherscript-redkit-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/bi3lu/witcherscript-redkit-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-654FF0)
![.NET 10](https://img.shields.io/badge/.NET-10.0-512BD4?logo=dotnet&logoColor=white)
![C# 14](https://img.shields.io/badge/C%23-14-239120?logo=csharp&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)
![Language Server Protocol](https://img.shields.io/badge/LSP-enabled-blue)

WitcherScript REDkit Tools is an unofficial developer toolkit for working with
WitcherScript source files and REDkit-style project layouts. It combines a Python
Language Server Protocol implementation, a REDkit-focused .NET command-line
tool, a VS Code client harness, and a fixture-driven test suite.

The repository is designed around a clear separation of responsibilities:
language analysis lives in Python, REDkit and Windows process integration lives
in C#, and editor integration talks to the language server through standard LSP.

## I Just Want To Use This In VS Code

1. Download the latest `.vsix` from
   [GitHub Releases](https://github.com/bi3lu/witcherscript-redkit-tools/releases).
2. Install it in VS Code with `Extensions: Install from VSIX...`.
3. Open your mod workspace.
4. Run `WitcherScript: Doctor Setup`.
5. Run `WitcherScript: Initialize REDkit Config`.
6. Set Witcher 3 / REDkit paths if the generated config does not detect them.

The extension uses `witcherscript.toml` as the project configuration file. The
initialize command creates that file for the current workspace, and the language
server uses it for indexing, diagnostics, completion, hover, definition, and
REDkit workflow commands. `Doctor Setup` checks the local toolchain, bundled
language server environment, REDkit CLI, project config, and configured paths,
then writes a setup checklist to the WitcherScript output panel.

## What It Provides

- **WitcherScript language server** with diagnostics, semantic highlighting,
  symbol indexing, go to definition, hover, references, completion, signature
  help, and semantic checks.
- **Developer CLI** for parsing `.ws` files and running diagnostics across
  WitcherScript corpora.
- **REDkit tooling CLI** for project detection, `witcherscript.toml` generation,
  validation, script recompilation adapters, and game launch adapters.
- **VS Code extension harness** for daily language-server testing with setup
  doctor, status feedback, output logs, restart support, and REDkit config
  initialization.
- **Portable development workflow** through `uv`, .NET SDK pinning, Docker,
  Dev Containers, GitHub Actions, and reproducible test fixtures.

## Feature Snapshot

| Area | Supported capabilities |
| --- | --- |
| Lexing and parsing | WitcherScript tokenization, structural AST, expression AST, parser recovery, snapshot coverage |
| Diagnostics | Lexer, parser, semantic, project, type, member, call, inheritance, duplicate symbol, and import diagnostics |
| Workspace model | `witcherscript.toml`, source roots, vanilla roots, exclude rules, file watching, refresh command |
| Symbol intelligence | Global symbols, per-file symbols, scope lookup, local variables, parameters, members, inheritance lookup |
| Editor features | Document symbols, workspace symbols, definition, implementation, hover, completion, code actions, references, rename, signature help, semantic highlighting |
| Type-aware completion | Type positions, `extends`, local scope, member access, keyword filtering, import suggestions |
| Corpus tooling | Multi-file corpus scans, diagnostics summaries, parser coverage reporting, timing measurements |
| REDkit tooling | Project detection, content repositories, config export, validation, recompile and launch process adapters |
| VS Code client | `.ws` activation, setup doctor, configurable LSP startup, status bar, output panel, restart and REDkit init commands |

## Repository Layout

```text
.
├─ docs/                         Project documentation
├─ samples/                      WitcherScript samples and workspace fixtures
├─ src/
│  ├─ py/                        Python language server and developer CLI
│  ├─ dotnet/                    C# REDkit tooling solution
│  └─ vscode/                    VS Code language-server client
├─ tests/py/                     Python tests, integration fixtures, and snapshots
├─ Dockerfile                    Development container image
├─ CHANGELOG.md                  Release history
├─ docker-compose.yml            Container workflow
├─ global.json                   .NET SDK pin
├─ Makefile                      Common local commands
├─ pyproject.toml                Python package and tooling configuration
├─ VERSION                       Release version source of truth
└─ uv.lock                       Locked Python dependencies
```

## Contributor Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- .NET SDK 10.0, selected by `global.json`
- Node.js 22 for the VS Code extension
- Docker, when using the container workflow

REDkit and The Witcher 3 are Windows-native tools. The language server, parser,
CLI tests, and VS Code extension checks run on macOS, Linux, and Windows. REDkit
process commands require paths to a real Windows installation.

## Contributor Quick Start

Install Python dependencies:

```bash
uv sync --all-extras --dev
```

Restore the .NET solution:

```bash
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
```

Install VS Code extension dependencies:

```bash
npm --prefix src/vscode ci
```

Parse a sample WitcherScript file:

```bash
uv run witcherscript parse samples/scripts/valid/minimal_class.ws
```

Run a corpus diagnostics report:

```bash
uv run witcherscript corpus samples/fixtures/corpus_project
```

Start the language server over standard input and output:

```bash
uv run witcherscript-lsp
```

The language server is normally launched by an LSP client. During initialization
it reads the workspace root, loads `witcherscript.toml` when present, indexes
configured `.ws` files, and keeps open documents synchronized with editor
changes.

## Developer CLI

The Python CLI is available through `uv run witcherscript`.

```bash
uv run witcherscript version
uv run witcherscript doctor
uv run witcherscript parse path/to/file.ws
uv run witcherscript corpus path/to/scripts
uv run witcherscript corpus path/to/scripts --no-semantic
```

`doctor` checks workspace health, project configuration, indexed files,
diagnostics, REDkit CLI availability, and recompile configuration. `parse` prints
a JSON representation of the parsed AST and diagnostics. `corpus` walks files
and directories, runs the analyzer, and prints aggregate diagnostics and parser
coverage data.

## REDkit CLI

The REDkit CLI lives in the .NET solution and can be run directly from source:

```bash
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- detect --project-dir <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- init --project-dir <path> --force
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- print-config --project-dir <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- validate --project-dir <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- recompile --project-dir <path> --executable <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- launch-game --project-dir <path>
```

`init` writes `witcherscript.toml`, which is the exchange format consumed by the
language server.

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

Relative paths are resolved from the workspace root. Absolute paths are used as
written. If the file is not present, the language server indexes the workspace
root with default exclude rules.

## VS Code Extension

The VS Code client harness is located in `src/vscode`.

```bash
npm --prefix src/vscode ci
npm --prefix src/vscode run compile
```

Open `src/vscode` in VS Code, start the `Run WitcherScript Extension` debug
configuration, and open a `.ws` file in the Extension Development Host.

Useful commands:

- `WitcherScript: Doctor Setup`
- `WitcherScript: Refresh Project Index`
- `WitcherScript: Initialize REDkit Config`
- `WitcherScript: Recompile Scripts`
- `WitcherScript: Launch Game`
- `WitcherScript: Restart Language Server`
- `WitcherScript: Show Output Logs`

See [docs/vscode-extension.md](docs/vscode-extension.md) for settings, launch
configuration, and troubleshooting notes.

## Quality Gates

GitHub Actions runs Python, .NET, and VS Code extension checks on `main` and
`develop` pull requests and pushes.

Run the same checks locally:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/py
uv run pytest --cov=src/py
dotnet test src/dotnet/WitcherScript.RedkitTooling.sln
npm --prefix src/vscode run smoke
```

Package the installable VS Code extension locally:

```bash
uv run python scripts/prepare_vscode_package.py
npm --prefix src/vscode run package:vsix -- --out ../../dist/witcherscript-redkit-tools.vsix
```

Published GitHub Releases automatically attach a `.vsix` asset.

Common shortcuts are available through `make`:

```bash
make sync
make lint
make test
make version-check
```

## Versioning

The repository uses [VERSION](VERSION) as the source of truth for release
metadata. The version is synchronized into Python package metadata, the Python
runtime package, the VS Code extension package files, and .NET project metadata.

Update the release version with:

```bash
uv run python scripts/sync_version.py
```

Check that metadata is synchronized with:

```bash
uv run python scripts/sync_version.py --check
```

Release changes are documented in [CHANGELOG.md](CHANGELOG.md).

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

See [docs/containers.md](docs/containers.md) for details about volumes, Dev
Containers, and Windows path mounts.

## Documentation

- [Architecture](docs/architecture.md)
- [Changelog](CHANGELOG.md)
- [Contributing](.github/CONTRIBUTING.md)
- [Language Server Features](docs/lsp-features.md)
- [REDkit Project Model](docs/redkit-project-model.md)
- [Security Policy](.github/SECURITY.md)
- [WitcherScript Language Notes](docs/witcherscript-notes.md)
- [Corpus Testing](docs/corpus.md)
- [VS Code Extension](docs/vscode-extension.md)
- [Containers](docs/containers.md)

## License

This project is licensed under the [MIT License](LICENSE).

This is an unofficial community project and is not affiliated with or endorsed by
CD PROJEKT RED.
