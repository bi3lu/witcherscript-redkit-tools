namespace WitcherScript.RedkitTooling;

public sealed record RedkitProject(
    string Name,
    string ProjectDirectory,
    string? GameDirectory,
    string? RedkitDirectory,
    IReadOnlyList<ContentRepository> ContentRepositories,
    IReadOnlyList<string> ScriptRoots
);
