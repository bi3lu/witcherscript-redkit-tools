namespace WitcherScript.RedkitTooling;

/// <summary>
/// Describes one validation finding for a REDkit project.
/// </summary>
/// <param name="Severity">Validation severity.</param>
/// <param name="Code">Stable diagnostic code.</param>
/// <param name="Message">Human-readable validation message.</param>
/// <param name="Path">Related filesystem path, when applicable.</param>
public sealed record ValidationMessage(
    ValidationSeverity Severity,
    string Code,
    string Message,
    string? Path = null
);
