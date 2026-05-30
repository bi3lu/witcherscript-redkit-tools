namespace WitcherScript.RedkitTooling;

/// <summary>
/// Provides optional manual paths used during REDkit project detection.
/// </summary>
/// <param name="ProjectDirectory">Project directory to inspect, or the current directory when omitted.</param>
/// <param name="GameDirectory">The Witcher 3 installation directory override.</param>
/// <param name="RedkitDirectory">REDkit installation directory override.</param>
public sealed record DetectionOptions(
    string? ProjectDirectory = null,
    string? GameDirectory = null,
    string? RedkitDirectory = null
);
