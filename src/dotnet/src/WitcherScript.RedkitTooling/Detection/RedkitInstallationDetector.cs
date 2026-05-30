namespace WitcherScript.RedkitTooling;

/// <summary>
/// Detects REDkit installation directories from manual, environment, and known paths.
/// </summary>
public sealed class RedkitInstallationDetector
{
    private readonly IReadOnlyList<string> _candidateDirectories;

    /// <summary>
    /// Initializes a new instance of the <see cref="RedkitInstallationDetector"/> class.
    /// </summary>
    /// <param name="candidateDirectories">Candidate directories checked after manual and environment paths.</param>
    public RedkitInstallationDetector(IEnumerable<string>? candidateDirectories = null)
    {
        _candidateDirectories = candidateDirectories?.ToArray() ?? DefaultCandidateDirectories();
    }

    /// <summary>
    /// Detects a valid REDkit installation directory.
    /// </summary>
    /// <param name="manualPath">Optional path supplied by the caller.</param>
    /// <returns>The full REDkit installation path when found; otherwise, <see langword="null"/>.</returns>
    public string? Detect(string? manualPath = null)
    {
        if (!string.IsNullOrWhiteSpace(manualPath) && IsRedkitDirectory(manualPath))
        {
            return Path.GetFullPath(manualPath);
        }

        var environmentPath = Environment.GetEnvironmentVariable("WITCHERSCRIPT_REDKIT_DIRECTORY");

        if (!string.IsNullOrWhiteSpace(environmentPath) && IsRedkitDirectory(environmentPath))
        {
            return Path.GetFullPath(environmentPath);
        }

        foreach (var candidate in _candidateDirectories)
        {
            if (IsRedkitDirectory(candidate))
            {
                return Path.GetFullPath(candidate);
            }
        }

        return null;
    }

    /// <summary>
    /// Determines whether a path looks like a REDkit installation directory.
    /// </summary>
    /// <param name="path">Path to inspect.</param>
    /// <returns><see langword="true"/> when the path contains expected REDkit files or folders.</returns>
    public static bool IsRedkitDirectory(string? path)
    {
        if (string.IsNullOrWhiteSpace(path) || !Directory.Exists(path))
        {
            return false;
        }

        return File.Exists(Path.Combine(path, "REDkit.exe"))
            || File.Exists(Path.Combine(path, "bin", "REDkit.exe"))
            || Directory.Exists(Path.Combine(path, "bin"));
    }

    private static string[] DefaultCandidateDirectories()
    {
        var candidates = new List<string>();

        if (OperatingSystem.IsWindows())
        {
            candidates.AddRange(
                [
                    @"C:\Program Files (x86)\Steam\steamapps\common\The Witcher 3 REDkit",
                    @"C:\Program Files\GOG Galaxy\Games\The Witcher 3 REDkit",
                ]
            );
        }

        return [.. candidates];
    }
}
