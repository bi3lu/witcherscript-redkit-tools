# WitcherScript REDkit Tools

[![CI](https://github.com/bi3lu/witcherscript-redkit-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/bi3lu/witcherscript-redkit-tools/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-managed-654FF0)
![.NET 10](https://img.shields.io/badge/.NET-10.0-512BD4?logo=dotnet&logoColor=white)
![C# 14](https://img.shields.io/badge/C%23-14-239120?logo=csharp&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)
![Language Server Protocol](https://img.shields.io/badge/LSP-enabled-blue)

WitcherScript REDkit Tools is an unofficial toolkit for editing, validating,
and navigating WitcherScript projects used with The Witcher 3 REDkit. It
provides a VS Code extension, a Python language server, developer CLI commands,
and a .NET REDkit workflow CLI.

The project is built around one rule: keep the language intelligence, REDkit
project tooling, and editor integration separate. That makes the same core
usable from VS Code, other LSP-capable editors, automated tests, and command
line workflows.

## For Modders Using VS Code

1. Download the latest `.vsix` from
   [GitHub Releases](https://github.com/bi3lu/witcherscript-redkit-tools/releases).
2. In VS Code, run `Extensions: Install from VSIX...`.
3. Open your REDkit mod workspace.
4. Run `WitcherScript: Doctor Setup`.
5. Run `WitcherScript: Initialize REDkit Config`.
6. Open a `.ws` file and use the editor normally.

`Doctor Setup` is the first command to run when something does not work. It
checks your workspace, `witcherscript.toml`, `uv`, .NET SDK, language server
environment, REDkit CLI command, current LSP status, Witcher 3 path, REDkit
path, script roots, vanilla script roots, and recompile executable setting. The
report is written to the WitcherScript output panel with concrete `OK`,
`WARNING`, and `ERROR` entries.

Packaged `.vsix` builds include the language server and REDkit CLI source. The
current package still uses local `uv` and .NET SDK installations to run those
bundled tools, but the extension now tells you exactly which requirement is
missing and where the failing command is configured.

## Editor Features

| Feature | What you get in VS Code |
| --- | --- |
| Diagnostics | Syntax, project, type, inheritance, call, member, duplicate symbol, and import diagnostics |
| Completion | Keywords, project symbols, type positions, `extends`, locals, parameters, fields, methods, and imports |
| Navigation | Document symbols, workspace symbols, go to definition, references, and implementations |
| Hover | Resolved symbol details, kind, type, container, and source location |
| Signature help | Function parameter hints with active argument tracking |
| Rename | Conservative rename for local variables and function parameters |
| Code actions | Quick fixes for missing config, typo-like symbol issues, missing semicolons, and missing braces |
| Semantic highlighting | Classes, functions, methods, fields, locals, parameters, built-in types, events, native symbols, and deprecated symbols |
| REDkit workflow | Config initialization, index refresh, script recompile command, game launch command, and setup doctor |

## Project Components

- **VS Code extension**: editor activation, commands, output panel, setup
  doctor, status bar, LSP lifecycle, and REDkit workflow buttons.
- **Python language server**: parser, analyzer, project index, diagnostics,
  completion, hover, definition, references, rename, semantic tokens, and
  signature help.
- **Python CLI**: parser inspection, project doctor, and corpus diagnostics.
- **.NET REDkit CLI**: REDkit project detection, `witcherscript.toml`
  generation, validation, recompile adapters, and game launch adapters.
- **Test fixtures**: sample projects, parser snapshots, semantic tests, LSP
  integration tests, and corpus coverage checks.

## Workspace Configuration

The language server reads `witcherscript.toml` from the workspace root. Create
it from VS Code with `WitcherScript: Initialize REDkit Config` or from the
REDkit CLI with `init`.

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
written. If the config file is missing, the language server can still index the
workspace root with default exclude rules, but project-aware features work best
with explicit script roots.

## VS Code Commands

- `WitcherScript: Doctor Setup`
- `WitcherScript: Initialize REDkit Config`
- `WitcherScript: Refresh Project Index`
- `WitcherScript: Recompile Scripts`
- `WitcherScript: Launch Game`
- `WitcherScript: Restart Language Server`
- `WitcherScript: Show Output Logs`

See [docs/vscode-extension.md](docs/vscode-extension.md) for settings,
packaging details, daily debugging, and troubleshooting guidance.

## Command Line Usage

Python developer CLI:

```bash
uv run witcherscript version
uv run witcherscript doctor
uv run witcherscript parse path/to/file.ws
uv run witcherscript corpus path/to/scripts
uv run witcherscript corpus path/to/scripts --no-semantic
```

REDkit CLI from source:

```bash
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- detect --project-dir <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- init --project-dir <path> --force
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- print-config --project-dir <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- validate --project-dir <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- recompile --project-dir <path> --executable <path>
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- launch-game --project-dir <path>
```

## Developer Setup

Requirements:

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- .NET SDK 10.0, selected by [global.json](global.json)
- Node.js 22 for the VS Code extension
- Docker, when using the container workflow

Install dependencies:

```bash
uv sync --all-extras --dev
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
npm --prefix src/vscode ci --prefer-online
```

Useful local commands:

```bash
uv run witcherscript parse samples/scripts/valid/minimal_class.ws
uv run witcherscript corpus samples/fixtures/corpus_project
uv run witcherscript-lsp
npm --prefix src/vscode run smoke
```

Run the same quality gates used by CI:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/py
uv run pytest --cov=src/py
dotnet test src/dotnet/WitcherScript.RedkitTooling.sln
npm --prefix src/vscode run smoke
uv run python scripts/sync_version.py --check
```

## Packaging The Extension

Build the installable VS Code package locally:

```bash
uv run python scripts/prepare_vscode_package.py
npm --prefix src/vscode run package:vsix -- --out ../../dist/witcherscript-redkit-tools.vsix
```

Published GitHub Releases attach a `.vsix` asset automatically.

## Repository Layout

```text
.
├─ docs/                         Project documentation
├─ samples/                      WitcherScript samples and workspace fixtures
├─ src/
│  ├─ py/                        Python language server and developer CLI
│  ├─ dotnet/                    C# REDkit tooling solution
│  └─ vscode/                    VS Code extension
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

## Versioning

[VERSION](VERSION) is the source of truth for release metadata. The value is
synchronized into Python package metadata, Python runtime package metadata, VS
Code extension package files, and .NET project metadata.

```bash
uv run python scripts/sync_version.py
uv run python scripts/sync_version.py --check
```

Release changes are documented in [CHANGELOG.md](CHANGELOG.md).

## Docker Workflow

```bash
docker compose build dev
docker compose run --rm dev make test
docker compose run --rm dev
```

See [docs/containers.md](docs/containers.md) for details about volumes, Dev
Containers, and Windows path mounts.

## Documentation

- [Architecture](docs/architecture.md)
- [Changelog](CHANGELOG.md)
- [Contributing](.github/CONTRIBUTING.md)
- [Corpus Testing](docs/corpus.md)
- [Language Server Features](docs/lsp-features.md)
- [REDkit Project Model](docs/redkit-project-model.md)
- [Security Policy](.github/SECURITY.md)
- [VS Code Extension](docs/vscode-extension.md)
- [WitcherScript Language Notes](docs/witcherscript-notes.md)
- [Containers](docs/containers.md)

## License

This project is licensed under the [MIT License](LICENSE).

This is an unofficial community project and is not affiliated with or endorsed
by CD PROJEKT RED.
