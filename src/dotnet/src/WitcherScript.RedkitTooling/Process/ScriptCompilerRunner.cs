namespace WitcherScript.RedkitTooling;

/// <summary>
/// Runs REDkit script recompilation commands for a detected project.
/// </summary>
public sealed class ScriptCompilerRunner
{
    private readonly IProcessRunner _processRunner;

    /// <summary>
    /// Initializes a new instance of the <see cref="ScriptCompilerRunner"/> class.
    /// </summary>
    /// <param name="processRunner">Process runner used to invoke external tooling.</param>
    public ScriptCompilerRunner(IProcessRunner processRunner)
    {
        _processRunner = processRunner;
    }

    /// <summary>
    /// Runs a script recompilation command for the specified REDkit project.
    /// </summary>
    /// <param name="project">Project whose scripts should be recompiled.</param>
    /// <param name="executablePath">Executable path for the external recompilation tool.</param>
    /// <param name="cancellationToken">Token used to cancel process execution.</param>
    /// <returns>The external process result.</returns>
    public Task<ProcessRunResult> RecompileAsync(
        RedkitProject project,
        string executablePath,
        CancellationToken cancellationToken = default
    )
    {
        var arguments = new[]
        {
            "recompile",
            "--project",
            project.ProjectDirectory,
        };
        return _processRunner.RunAsync(
            executablePath,
            arguments,
            project.ProjectDirectory,
            cancellationToken
        );
    }
}
