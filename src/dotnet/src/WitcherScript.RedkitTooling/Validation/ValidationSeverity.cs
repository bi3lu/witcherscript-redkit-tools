namespace WitcherScript.RedkitTooling;

/// <summary>
/// Defines severity levels for REDkit project validation messages.
/// </summary>
public enum ValidationSeverity
{
    /// <summary>
    /// Informational validation message.
    /// </summary>
    Info,

    /// <summary>
    /// Non-blocking validation warning.
    /// </summary>
    Warning,

    /// <summary>
    /// Blocking validation error.
    /// </summary>
    Error
}
