using System.Text.RegularExpressions;

namespace WitcherScript.RedkitTooling;

/// <summary>
/// Parses warnings and errors from script recompilation output.
/// </summary>
public sealed partial class RecompileLogParser
{
    /// <summary>
    /// Parses a process result into a structured recompilation summary.
    /// </summary>
    /// <param name="result">External process result.</param>
    /// <returns>Parsed recompilation summary.</returns>
    public RecompileLogSummary Parse(ProcessRunResult result)
    {
        var entries = new List<RecompileLogEntry>();
        ParseStream(result.StandardOutput, entries);
        ParseStream(result.StandardError, entries);

        return new RecompileLogSummary(result.ExitCode, entries);
    }

    private static void ParseStream(string stream, List<RecompileLogEntry> entries)
    {
        foreach (var line in stream.Split(["\r\n", "\n"], StringSplitOptions.RemoveEmptyEntries))
        {
            var entry = ParseLine(line);
            if (entry is not null)
            {
                entries.Add(entry);
            }
        }
    }

    private static RecompileLogEntry? ParseLine(string line)
    {
        var compilerMatch = CompilerLogPattern().Match(line);
        if (compilerMatch.Success)
        {
            return new RecompileLogEntry(
                SeverityFrom(compilerMatch.Groups["severity"].Value),
                compilerMatch.Groups["code"].Value.Trim(),
                compilerMatch.Groups["message"].Value.Trim(),
                compilerMatch.Groups["file"].Value.Trim(),
                ParseInt(compilerMatch.Groups["line"].Value),
                ParseInt(compilerMatch.Groups["column"].Value)
            );
        }

        var simpleMatch = SimpleLogPattern().Match(line);
        if (!simpleMatch.Success)
        {
            return null;
        }

        var severity = SeverityFrom(simpleMatch.Groups["severity"].Value);
        var code = severity == ValidationSeverity.Warning ? "WSR0002" : "WSR0001";
        return new RecompileLogEntry(severity, code, simpleMatch.Groups["message"].Value.Trim());
    }

    private static ValidationSeverity SeverityFrom(string value)
    {
        return value.Equals("warning", StringComparison.OrdinalIgnoreCase)
            ? ValidationSeverity.Warning
            : ValidationSeverity.Error;
    }

    private static int? ParseInt(string value)
    {
        return int.TryParse(value, out var parsed) ? parsed : null;
    }

    [GeneratedRegex(
        @"^(?<file>.+?\.ws)\((?<line>\d+)(,(?<column>\d+))?\):\s*(?<severity>error|warning)\s*(?<code>[^:]+):\s*(?<message>.+)$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex CompilerLogPattern();

    [GeneratedRegex(
        @"\b(?<severity>error|warning)\b\s*:?\s*(?<message>.+)$",
        RegexOptions.IgnoreCase | RegexOptions.CultureInvariant
    )]
    private static partial Regex SimpleLogPattern();
}
