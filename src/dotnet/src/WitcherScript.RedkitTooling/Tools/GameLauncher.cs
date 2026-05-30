namespace WitcherScript.RedkitTooling;

/// <summary>
/// Launches The Witcher 3 for a detected REDkit project.
/// </summary>
public sealed class GameLauncher
{
    private readonly IProcessRunner _processRunner;

    /// <summary>
    /// Initializes a new instance of the <see cref="GameLauncher"/> class.
    /// </summary>
    /// <param name="processRunner">Process runner used to start the game executable.</param>
    public GameLauncher(IProcessRunner processRunner)
    {
        _processRunner = processRunner;
    }

    /// <summary>
    /// Launches the game executable with the supplied arguments.
    /// </summary>
    /// <param name="project">Project used to resolve the working directory.</param>
    /// <param name="executablePath">Path to the game executable.</param>
    /// <param name="arguments">Arguments passed to the executable.</param>
    /// <param name="cancellationToken">Token used to cancel process execution.</param>
    /// <returns>The external process result.</returns>
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
