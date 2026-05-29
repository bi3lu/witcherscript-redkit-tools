# REDkit Project Model

The REDkit tooling project defines a strongly typed representation of a REDkit workspace. The model is intentionally separate from the language server so REDkit-specific filesystem and process concerns stay outside the Python language-analysis core.

## Project Record

`RedkitProject` represents one REDkit project:

```csharp
public sealed record RedkitProject(
    string Name,
    string ProjectDirectory,
    string? GameDirectory,
    string? RedkitDirectory,
    IReadOnlyList<ContentRepository> ContentRepositories,
    IReadOnlyList<string> ScriptRoots
);
```

Fields:

- `Name`: project display name
- `ProjectDirectory`: REDkit project directory
- `GameDirectory`: The Witcher 3 installation directory, when configured
- `RedkitDirectory`: REDkit installation directory, when configured
- `ContentRepositories`: ordered content repositories used by the project
- `ScriptRoots`: directories containing WitcherScript source files

## Content Repositories

`ContentRepository` describes a content source available to the project.

Repository kinds:

- `Vanilla`
- `Dlc`
- `Mod`
- `Project`

The `LoadOrder` value is part of the model because script and content resolution depend on deterministic repository ordering.

## Configuration Boundary

The language server reads `witcherscript.toml`. REDkit tooling owns REDkit-oriented project data and can represent the same paths in C#:

```toml
[project]
name = "MyRedkitMod"

[redkit]
game_directory = "D:/Steam/steamapps/common/The Witcher 3"
redkit_directory = "D:/Steam/steamapps/common/The Witcher 3 REDkit"
project_directory = "D:/REDkitProjects/MyMod"

[scripts]
source_roots = ["content/scripts"]
vanilla_roots = ["D:/Steam/steamapps/common/The Witcher 3/content/content0/scripts"]
exclude = ["**/bin/**", "**/.cache/**", "**/.ws-cache/**", "**/generated/**"]
```

The configuration boundary is simple:

- Python reads the TOML file and indexes scripts.
- C# owns REDkit project data and command-line tooling.
- Both sides use explicit paths rather than implicit global state.

## Path Handling

The model supports manual paths for the game, REDkit, project directory, and script roots. This avoids assuming one installation layout and keeps Steam, GOG, custom library, and portable setups representable.

Relative paths in `witcherscript.toml` are resolved from the workspace root by the language server. Absolute paths are preserved.

## CLI

The REDkit CLI project builds as part of the .NET solution and exposes a version command:

```bash
dotnet run --project src/dotnet/src/WitcherScript.RedkitTooling.Cli -- --version
```

Output:

```text
ws-redkit 0.1.0
```
