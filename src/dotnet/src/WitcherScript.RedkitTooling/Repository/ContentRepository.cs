namespace WitcherScript.RedkitTooling;

/// <summary>
/// Represents a content repository that can contribute scripts or assets to a REDkit project.
/// </summary>
/// <param name="Name">Repository display name.</param>
/// <param name="Path">Filesystem path to the repository root.</param>
/// <param name="Kind">Repository category.</param>
/// <param name="LoadOrder">Deterministic ordering value used when multiple repositories are present.</param>
public sealed record ContentRepository(
    string Name,
    string Path,
    ContentRepositoryKind Kind,
    int LoadOrder
);
