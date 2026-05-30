namespace WitcherScript.RedkitTooling;

/// <summary>
/// Represents a REDkit project and the script repositories available to it.
/// </summary>
/// <param name="Name">Project display name.</param>
/// <param name="ProjectDirectory">Root directory of the REDkit project.</param>
/// <param name="GameDirectory">The Witcher 3 installation directory, when known.</param>
/// <param name="RedkitDirectory">REDkit installation directory, when known.</param>
/// <param name="ContentRepositories">Ordered content repositories participating in the project.</param>
/// <param name="ScriptRoots">Directories containing WitcherScript source files.</param>
public sealed record RedkitProject(
    string Name,
    string ProjectDirectory,
    string? GameDirectory,
    string? RedkitDirectory,
    IReadOnlyList<ContentRepository> ContentRepositories,
    IReadOnlyList<string> ScriptRoots
);
