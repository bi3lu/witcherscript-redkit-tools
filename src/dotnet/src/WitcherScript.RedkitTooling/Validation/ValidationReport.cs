namespace WitcherScript.RedkitTooling;

/// <summary>
/// Aggregates validation messages produced for a REDkit project.
/// </summary>
/// <param name="Messages">Validation messages in report order.</param>
public sealed record ValidationReport(IReadOnlyList<ValidationMessage> Messages)
{
    /// <summary>
    /// Gets a value indicating whether the report contains no error messages.
    /// </summary>
    public bool IsValid => Messages.All(message => message.Severity != ValidationSeverity.Error);
}
