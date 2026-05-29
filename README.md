# WitcherScript REDkit Tools

Developer tooling for WitcherScript and REDkit projects.

The project starts with two reusable foundations:

- **WitcherScript Language Server** written in Python.
- **REDkit Project Tooling CLI** written in C#.

The goal is to build a solid language and project core first, then reuse it from VS Code, a custom IDE, other LSP-capable editors, and standalone CLI workflows.

## Status

Early foundation work. The repository currently contains project structure, quality tooling, CI configuration, and minimal smoke tests.

## Roadmap

- `v0.1`: repository foundation, lexer model, parser skeleton, parse CLI.
- `v0.2`: minimal LSP with diagnostics and document symbols.
- `v0.3`: workspace config, project index, go to definition.
- `v0.4`: completion and hover MVP.
- `v0.5`: REDkit tooling MVP for detect/init/validate.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/)
- .NET 10 SDK for C# 14

## Local Development

Install Python dependencies:

```bash
uv sync
```

Run Python checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/py
uv run pytest
```

Run .NET checks:

```bash
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
dotnet build src/dotnet/WitcherScript.RedkitTooling.sln --configuration Release --no-restore
dotnet test src/dotnet/WitcherScript.RedkitTooling.sln --configuration Release --no-build
```

Or use the Makefile shortcuts:

```bash
make test
make lint
```

## Containers

The repository includes Docker and VS Code Dev Container support for a consistent Python/.NET toolchain on macOS and Windows:

```bash
docker compose build dev
docker compose run --rm dev make test
```

See [docs/containers.md](docs/containers.md) for details. REDkit and The Witcher 3 should still be installed and launched natively on the Windows host.

## Architecture

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

Python owns language intelligence: parsing, diagnostics, symbols, completion, hover, definitions, and indexing.

C# owns REDkit integration: installation detection, project detection, path validation, config export, external process execution, and later game/tool launch workflows.
