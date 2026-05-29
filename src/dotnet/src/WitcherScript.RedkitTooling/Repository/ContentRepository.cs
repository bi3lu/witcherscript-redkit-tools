namespace WitcherScript.RedkitTooling;

public sealed record ContentRepository(
    string Name,
    string Path,
    ContentRepositoryKind Kind,
    int LoadOrder
);
