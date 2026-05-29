namespace WitcherScript.RedkitTooling;

public sealed record ValidationMessage(
    ValidationSeverity Severity,
    string Code,
    string Message,
    string? Path = null
);
