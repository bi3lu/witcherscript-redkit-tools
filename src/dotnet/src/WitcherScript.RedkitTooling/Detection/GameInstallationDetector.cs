namespace WitcherScript.RedkitTooling;

/// <summary>
/// Detects The Witcher 3 installation directories from manual, environment, and known paths.
/// </summary>
public sealed class GameInstallationDetector
{
    private readonly IReadOnlyList<string> _candidateDirectories;

    /// <summary>
    /// Initializes a new instance of the <see cref="GameInstallationDetector"/> class.
    /// </summary>
    /// <param name="candidateDirectories">Candidate directories checked after manual and environment paths.</param>
    public GameInstallationDetector(IEnumerable<string>? candidateDirectories = null)
    {
        _candidateDirectories = candidateDirectories?.ToArray() ?? DefaultCandidateDirectories();
    }

    /// <summary>
    /// Detects a valid The Witcher 3 installation directory.
    /// </summary>
    /// <param name="manualPath">Optional path supplied by the caller.</param>
    /// <returns>The full installation path when found; otherwise, <see langword="null"/>.</returns>
    public string? Detect(string? manualPath = null)
    {
        if (!string.IsNullOrWhiteSpace(manualPath) && IsGameDirectory(manualPath))
        {
            return Path.GetFullPath(manualPath);
        }

        var environmentPath = Environment.GetEnvironmentVariable("WITCHERSCRIPT_GAME_DIRECTORY");

        if (!string.IsNullOrWhiteSpace(environmentPath) && IsGameDirectory(environmentPath))
        {
            return Path.GetFullPath(environmentPath);
        }

        foreach (var candidate in _candidateDirectories)
        {
            if (IsGameDirectory(candidate))
            {
                return Path.GetFullPath(candidate);
            }
        }

        return null;
    }

    /// <summary>
    /// Determines whether a path looks like a The Witcher 3 installation directory.
    /// </summary>
    /// <param name="path">Path to inspect.</param>
    /// <returns><see langword="true"/> when the path contains expected game files or script folders.</returns>
    public static bool IsGameDirectory(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || !Directory.Exists(path))
        {
            return false;
        }

        return File.Exists(Path.Combine(path, "bin", "x64", "witcher3.exe"))
            || File.Exists(Path.Combine(path, "bin", "x64_dx12", "witcher3.exe"))
            || Directory.Exists(Path.Combine(path, "content", "content0", "scripts"));
    }

    private static string[] DefaultCandidateDirectories()
    {
        var candidates = new List<string>();

        if (OperatingSystem.IsWindows())
        {
            candidates.AddRange(
                [
                    @"C:\Program Files (x86)\Steam\steamapps\common\The Witcher 3",
                    @"C:\Program Files\GOG Galaxy\Games\The Witcher 3 Wild Hunt",
                    @"C:\GOG Games\The Witcher 3 Wild Hunt",
                ]
            );
        }

        return [.. candidates];
    }
}
