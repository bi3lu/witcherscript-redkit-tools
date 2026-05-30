namespace WitcherScript.RedkitTooling;

/// <summary>
/// Runs external processes for REDkit tooling commands.
/// </summary>
public interface IProcessRunner
{
    /// <summary>
    /// Runs an external process and captures its output.
    /// </summary>
    /// <param name="fileName">Executable path or command name.</param>
    /// <param name="arguments">Arguments passed to the process.</param>
    /// <param name="workingDirectory">Optional working directory for the process.</param>
    /// <param name="cancellationToken">Token used to cancel process execution.</param>
    /// <returns>The process exit code and captured output streams.</returns>
    Task<ProcessRunResult> RunAsync(
        string fileName,
        IReadOnlyList<string> arguments,
        string? workingDirectory,
        CancellationToken cancellationToken = default
    );
}
