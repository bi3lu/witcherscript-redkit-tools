namespace WitcherScript.RedkitTooling;

public sealed class GameInstallationDetector
{
    private readonly IReadOnlyList<string> _candidateDirectories;

    public GameInstallationDetector(IEnumerable<string>? candidateDirectories = null)
    {
        _candidateDirectories = candidateDirectories?.ToArray() ?? DefaultCandidateDirectories();
    }

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
