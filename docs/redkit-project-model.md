# REDkit Project Model

The C# tooling should produce a structured REDkit project model that can be exported to `witcherscript.toml`.

Configuration source priority:

1. CLI arguments
2. environment variables
3. `witcherscript.toml`
4. known Steam/GOG paths
5. folder heuristics

Detection must be conservative and allow manual overrides.
