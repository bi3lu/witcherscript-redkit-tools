namespace WitcherScript.RedkitTooling;

public sealed record ProcessRunResult(
    int ExitCode,
    string StandardOutput,
    string StandardError
);
