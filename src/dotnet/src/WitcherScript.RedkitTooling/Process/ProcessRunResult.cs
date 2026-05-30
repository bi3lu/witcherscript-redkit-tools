namespace WitcherScript.RedkitTooling;

/// <summary>
/// Captures the result of an external process invocation.
/// </summary>
/// <param name="ExitCode">Process exit code.</param>
/// <param name="StandardOutput">Captured standard output text.</param>
/// <param name="StandardError">Captured standard error text.</param>
public sealed record ProcessRunResult(
    int ExitCode,
    string StandardOutput,
    string StandardError
);
