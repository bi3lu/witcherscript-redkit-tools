namespace WitcherScript.RedkitTooling;

/// <summary>
/// Summarizes parsed output from a REDkit script recompilation command.
/// </summary>
/// <param name="ExitCode">External process exit code.</param>
/// <param name="Entries">Parsed warnings and errors.</param>
public sealed record RecompileLogSummary(int ExitCode, IReadOnlyList<RecompileLogEntry> Entries)
{
    /// <summary>
    /// Gets the number of parsed error messages.
    /// </summary>
    public int ErrorCount => Entries.Count(entry => entry.Severity == ValidationSeverity.Error);

    /// <summary>
    /// Gets the number of parsed warning messages.
    /// </summary>
    public int WarningCount => Entries.Count(entry => entry.Severity == ValidationSeverity.Warning);

    /// <summary>
    /// Gets a value indicating whether the recompilation output contains errors.
    /// </summary>
    public bool HasErrors => ExitCode != 0 || ErrorCount > 0;
}
