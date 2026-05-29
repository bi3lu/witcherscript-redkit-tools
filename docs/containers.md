# Containers

The repository includes a Docker-based development environment for keeping Python, uv, and the .NET SDK consistent across machines.

The container is intended for repository development: tests, linting, parser work, language server work, and .NET solution checks. REDkit and The Witcher 3 remain Windows-native applications installed on the Windows host.

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

The compose configuration mounts the repository at `/workspace` and uses named volumes for:

- Python virtual environment: `/workspace/.venv`
- uv cache: `/root/.cache/uv`
- NuGet packages: `/root/.nuget/packages`

Named volumes keep host-specific dependency artifacts out of the repository and avoid conflicts between macOS and Windows filesystems.

## Dev Container

The VS Code Dev Container configuration uses the same `Dockerfile` and Docker Compose service.

Open the repository in VS Code and run:

```text
Dev Containers: Reopen in Container
```

The container restores Python and .NET dependencies during setup:

```bash
uv sync --all-extras --dev --frozen
dotnet restore src/dotnet/WitcherScript.RedkitTooling.sln
```

## Windows REDkit Mounts

For checks that need access to local REDkit or game folders, create a machine-local `docker-compose.override.yml`:

```yaml
services:
  dev:
    volumes:
      - D:/REDkitProjects:/redkit/projects
      - D:/Steam/steamapps/common/The Witcher 3:/redkit/game:ro
      - D:/Steam/steamapps/common/The Witcher 3 REDkit:/redkit/redkit:ro
```

Do not commit machine-specific override files.

## Useful Commands

Inside the container:

```bash
make sync
make lint
make test
uv run witcherscript-lsp
dotnet test src/dotnet/WitcherScript.RedkitTooling.sln
```

The container runs Linux. Use native Windows execution for REDkit and game processes.
