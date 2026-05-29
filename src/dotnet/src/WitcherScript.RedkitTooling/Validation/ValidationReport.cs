namespace WitcherScript.RedkitTooling;

public sealed record ValidationReport(IReadOnlyList<ValidationMessage> Messages)
{
    public bool IsValid => Messages.All(message => message.Severity != ValidationSeverity.Error);
}
