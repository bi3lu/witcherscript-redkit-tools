namespace WitcherScript.RedkitTooling;

public sealed record ToolDetectionResult(
    string? GameDirectory,
    string? RedkitDirectory,
    string ProjectDirectory,
    IReadOnlyList<string> ScriptRoots
);
