# Contributing

Thank you for helping improve WitcherScript REDkit Tools. This project is built
around small, well-tested changes that keep the language server, REDkit tooling,
and VS Code client easy to reason about.

## Development Setup

Install the required toolchains:

- Python 3.12
- `uv`
- .NET SDK 10.0, selected by `global.json`
- Node.js 22 for the VS Code extension

Install dependencies:

```bash
uv sync --all-extras --dev
npm --prefix src/vscode ci
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
```

## Quality Checks

Run the main checks before opening a pull request:

```bash
uv run python scripts/sync_version.py --check
uv run ruff check .
uv run ruff format --check .
uv run mypy src/py
uv run pytest
dotnet test src/dotnet/WitcherScript.RedkitTooling.sln
npm --prefix src/vscode run smoke
git diff --check
```

## Pull Request Guidelines

- Keep changes focused on one behavior or project area.
- Add tests for language behavior, parser behavior, REDkit detection, or VS Code
  commands whenever behavior changes.
- Prefer fixtures under `samples/fixtures` for reusable language-server cases.
- Keep README user-facing and concise; put deeper engineering details under
  `docs/`.
- Update `CHANGELOG.md` for release-facing changes.

## Versioning

`VERSION` is the source of truth for release metadata. After changing it, run:

```bash
uv run python scripts/sync_version.py
```

CI verifies that package metadata matches `VERSION`.

## Reporting Issues

Use the most specific issue template available. Parser bugs, REDkit path/config
issues, and VS Code extension issues need different details, and the templates
ask for the information needed to reproduce them.
