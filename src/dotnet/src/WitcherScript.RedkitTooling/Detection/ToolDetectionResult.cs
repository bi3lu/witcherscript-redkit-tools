namespace WitcherScript.RedkitTooling;

/// <summary>
/// Describes the filesystem paths discovered by the REDkit tooling detector.
/// </summary>
/// <param name="GameDirectory">Detected The Witcher 3 installation directory.</param>
/// <param name="RedkitDirectory">Detected REDkit installation directory.</param>
/// <param name="ProjectDirectory">Detected REDkit project directory.</param>
/// <param name="ScriptRoots">Detected WitcherScript source roots.</param>
public sealed record ToolDetectionResult(
    string? GameDirectory,
    string? RedkitDirectory,
    string ProjectDirectory,
    IReadOnlyList<string> ScriptRoots
);
