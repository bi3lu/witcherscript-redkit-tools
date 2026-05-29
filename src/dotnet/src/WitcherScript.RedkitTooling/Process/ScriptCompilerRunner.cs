namespace WitcherScript.RedkitTooling;

public sealed class ScriptCompilerRunner
{
    private readonly IProcessRunner _processRunner;

    public ScriptCompilerRunner(IProcessRunner processRunner)
    {
        _processRunner = processRunner;
    }

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
