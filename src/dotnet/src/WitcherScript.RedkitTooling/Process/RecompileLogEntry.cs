namespace WitcherScript.RedkitTooling;

/// <summary>
/// Describes one parsed recompilation log message.
/// </summary>
/// <param name="Severity">Message severity.</param>
/// <param name="Code">Stable code when one is present in the external output.</param>
/// <param name="Message">Human-readable message.</param>
/// <param name="File">Source file path associated with the message.</param>
/// <param name="Line">One-based source line associated with the message.</param>
/// <param name="Column">One-based source column associated with the message.</param>
public sealed record RecompileLogEntry(
    ValidationSeverity Severity,
    string Code,
    string Message,
    string? File = null,
    int? Line = null,
    int? Column = null
);
