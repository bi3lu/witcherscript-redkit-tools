namespace WitcherScript.RedkitTooling;

public sealed class GameLauncher
{
    private readonly IProcessRunner _processRunner;

    public GameLauncher(IProcessRunner processRunner)
    {
        _processRunner = processRunner;
    }

    public Task<ProcessRunResult> LaunchAsync(
        RedkitProject project,
        string executablePath,
        IReadOnlyList<string> arguments,
        CancellationToken cancellationToken = default
    )
    {
        var workingDirectory = project.GameDirectory ?? Path.GetDirectoryName(executablePath);
        return _processRunner.RunAsync(
            executablePath,
            arguments,
            workingDirectory,
            cancellationToken
        );
    }
}
