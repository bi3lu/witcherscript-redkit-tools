using System.Diagnostics;

namespace WitcherScript.RedkitTooling;

public sealed class ProcessRunner : IProcessRunner
{
    public async Task<ProcessRunResult> RunAsync(
        string fileName,
        IReadOnlyList<string> arguments,
        string? workingDirectory,
        CancellationToken cancellationToken = default
    )
    {
        var startInfo = new ProcessStartInfo(fileName)
        {
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            UseShellExecute = false,
        };

        if (!string.IsNullOrWhiteSpace(workingDirectory))
        {
            startInfo.WorkingDirectory = workingDirectory;
        }

        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException($"Failed to start process: {fileName}");
        var stdout = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderr = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken).ConfigureAwait(false);

        return new ProcessRunResult(
            process.ExitCode,
            await stdout.ConfigureAwait(false),
            await stderr.ConfigureAwait(false)
        );
    }
}
