# Containers

This repository includes a development container for keeping the Python and .NET toolchain consistent across macOS and Windows.

The container is meant for repository development, tests, linting, parser work, language server work, and the REDkit CLI codebase. REDkit and The Witcher 3 are Windows-native tools and should still be installed and launched on the Windows host.

## Docker Compose

Build the development image:

```bash
docker compose build dev
```

Open a shell:

```bash
docker compose run --rm dev
```

Run checks:

```bash
docker compose run --rm dev make lint
docker compose run --rm dev make test
```

The compose setup uses named volumes for `.venv`, uv cache, and NuGet packages so macOS and Windows do not fight over host-specific dependency folders.

## VS Code Dev Container

Open the repository in VS Code and run:

```text
Dev Containers: Reopen in Container
```

The dev container builds from the same `Dockerfile` and runs:

```bash
uv sync --all-extras --dev --frozen
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
```

## REDkit on Windows

Use the container for building and testing the tooling itself. Use native Windows paths and native process launching for workflows that need REDkit or The Witcher 3. Later CLI commands can read mounted project folders, but launching REDkit/game executables from a Linux container is not the primary workflow.

For path validation experiments on Windows, create a local `docker-compose.override.yml` that mounts your own folders:

```yaml
services:
  dev:
    volumes:
      - D:/REDkitProjects:/redkit/projects
      - D:/Steam/steamapps/common/The Witcher 3:/redkit/game:ro
      - D:/Steam/steamapps/common/The Witcher 3 REDkit:/redkit/redkit:ro
```

Do not commit machine-specific overrides.
