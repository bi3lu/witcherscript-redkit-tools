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
            AddWindowsStorefrontCandidates(candidates, "The Witcher 3");
            AddWindowsStorefrontCandidates(candidates, "The Witcher 3 Wild Hunt");
        }

        return [.. candidates];
    }

    private static void AddWindowsStorefrontCandidates(List<string> candidates, string gameFolderName)
    {
        foreach (var programFilesPath in ProgramFilesPaths())
        {
            candidates.Add(Path.Combine(programFilesPath, "Steam", "steamapps", "common", gameFolderName));
            candidates.Add(Path.Combine(programFilesPath, "GOG Galaxy", "Games", gameFolderName));
            candidates.Add(Path.Combine(programFilesPath, "Epic Games", gameFolderName));
        }

        foreach (var drive in FixedWindowsDriveRoots())
        {
            candidates.Add(Path.Combine(drive, "SteamLibrary", "steamapps", "common", gameFolderName));
            candidates.Add(Path.Combine(drive, "Steam", "steamapps", "common", gameFolderName));
            candidates.Add(Path.Combine(drive, "GOG Games", gameFolderName));
            candidates.Add(Path.Combine(drive, "Games", gameFolderName));
        }
    }

    private static IEnumerable<string> ProgramFilesPaths()
    {
        foreach (var variable in new[] { "ProgramFiles(x86)", "ProgramFiles", "ProgramW6432" })
        {
            var path = Environment.GetEnvironmentVariable(variable);
            if (!string.IsNullOrWhiteSpace(path))
            {
                yield return path;
            }
        }
    }

    private static IEnumerable<string> FixedWindowsDriveRoots()
    {
        foreach (var drive in new[] { "C", "D", "E", "F", "G" })
        {
            yield return $"{drive}:\\";
        }
    }
}
