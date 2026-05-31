using System.Text.Json;
using WitcherScript.RedkitTooling;

namespace WitcherScript.RedkitTooling.Cli;

internal static class Program
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
        WriteIndented = true,
    };

    private static async Task<int> Main(string[] args)
    {
        if (args is ["--version"] or ["version"])
        {
            Console.WriteLine("ws-redkit 0.1.0");
            return 0;
        }

        if (args.Length == 0)
        {
            PrintHelp();
            return 0;
        }

        try
        {
            return await DispatchAsync(args).ConfigureAwait(false);
        }
        catch (Exception exception) when (exception is IOException or ArgumentException)
        {
            Console.Error.WriteLine(exception.Message);
            return 1;
        }
    }

    private static async Task<int> DispatchAsync(string[] args)
    {
        var command = args[0];
        var options = CommandOptions.Parse(args[1..]);

        return command switch
        {
            "detect" => Detect(options),
            "init" => Init(options),
            "print-config" => PrintConfig(options),
            "validate" => Validate(options),
            "recompile" => await RecompileAsync(options).ConfigureAwait(false),
            "launch-game" => await LaunchGameAsync(options).ConfigureAwait(false),
            _ => UnknownCommand(command),
        };
    }

    private static int Detect(CommandOptions options)
    {
        var detector = new RedkitProjectDetector();
        var result = detector.DetectResult(options.ToDetectionOptions());
        Console.WriteLine(JsonSerializer.Serialize(result, JsonOptions));
        return 0;
    }

    private static int Init(CommandOptions options)
    {
        var detector = new RedkitProjectDetector();
        var project = detector.Detect(options.ToDetectionOptions());
        var configPath = Path.Combine(project.ProjectDirectory, "witcherscript.toml");
        var result = new WitcherScriptConfigWriter().WriteToFile(project, configPath, options.Force);

        if (options.Json)
        {
            Console.WriteLine(JsonSerializer.Serialize(result, JsonOptions));
            return 0;
        }

        Console.WriteLine($"Wrote WitcherScript configuration: {result.Path}");
        if (result.BackupPath is not null)
        {
            Console.WriteLine($"Backed up previous configuration: {result.BackupPath}");
        }

        return 0;
    }

    private static int PrintConfig(CommandOptions options)
    {
        var detector = new RedkitProjectDetector();
        var project = detector.Detect(options.ToDetectionOptions());
        Console.Write(new WitcherScriptConfigWriter().Write(project));
        return 0;
    }

    private static int Validate(CommandOptions options)
    {
        var detector = new RedkitProjectDetector();
        var project = detector.Detect(options.ToDetectionOptions());
        var report = new RedkitProjectValidator().Validate(project);

        if (options.Json)
        {
            Console.WriteLine(JsonSerializer.Serialize(report, JsonOptions));
            return report.IsValid ? 0 : 1;
        }

        Console.WriteLine("REDkit project validation");
        Console.WriteLine($"Project: {project.ProjectDirectory}");
        Console.WriteLine($"Status: {(report.IsValid ? "OK" : "FAILED")}");
        Console.WriteLine();

        foreach (var message in report.Messages)
        {
            var path = string.IsNullOrWhiteSpace(message.Path) ? string.Empty : $" ({message.Path})";
            Console.WriteLine($"[{message.Severity}] {message.Code}: {message.Message}{path}");
        }

        return report.IsValid ? 0 : 1;
    }

    private static async Task<int> RecompileAsync(CommandOptions options)
    {
        var executable = options.Executable
            ?? throw new ArgumentException("Missing required option: --executable");
        var detector = new RedkitProjectDetector();
        var project = detector.Detect(options.ToDetectionOptions());
        var result = await new ScriptCompilerRunner(new ProcessRunner())
            .RecompileAsync(project, executable)
            .ConfigureAwait(false);
        var summary = new RecompileLogParser().Parse(result);

        if (options.Json)
        {
            Console.WriteLine(JsonSerializer.Serialize(summary, JsonOptions));
            return result.ExitCode;
        }

        PrintProcessResult(result);
        PrintRecompileSummary(summary);
        return result.ExitCode;
    }

    private static async Task<int> LaunchGameAsync(CommandOptions options)
    {
        var detector = new RedkitProjectDetector();
        var project = detector.Detect(options.ToDetectionOptions());
        var executable = options.Executable ?? DefaultGameExecutable(project);
        var result = await new GameLauncher(new ProcessRunner())
            .LaunchAsync(project, executable, options.Arguments)
            .ConfigureAwait(false);
        PrintProcessResult(result);
        return result.ExitCode;
    }

    private static string DefaultGameExecutable(RedkitProject project)
    {
        if (string.IsNullOrWhiteSpace(project.GameDirectory))
        {
            throw new ArgumentException("Missing required option: --executable");
        }

        var dx12 = Path.Combine(project.GameDirectory, "bin", "x64_dx12", "witcher3.exe");
        if (File.Exists(dx12))
        {
            return dx12;
        }

        return Path.Combine(project.GameDirectory, "bin", "x64", "witcher3.exe");
    }

    private static void PrintProcessResult(ProcessRunResult result)
    {
        if (!string.IsNullOrWhiteSpace(result.StandardOutput))
        {
            Console.Write(result.StandardOutput);
        }

        if (!string.IsNullOrWhiteSpace(result.StandardError))
        {
            Console.Error.Write(result.StandardError);
        }
    }

    private static void PrintRecompileSummary(RecompileLogSummary summary)
    {
        Console.WriteLine();
        Console.WriteLine(
            $"Recompile summary: exit {summary.ExitCode}, {summary.ErrorCount} error(s), {summary.WarningCount} warning(s)."
        );

        foreach (var entry in summary.Entries)
        {
            var location = entry.File is null ? string.Empty : $" {entry.File}";
            if (entry.Line is not null)
            {
                location += $":{entry.Line}";
            }

            if (entry.Column is not null)
            {
                location += $":{entry.Column}";
            }

            Console.WriteLine($"[{entry.Severity}] {entry.Code}:{location} {entry.Message}");
        }
    }

    private static int UnknownCommand(string command)
    {
        Console.Error.WriteLine($"Unknown command: {command}");
        PrintHelp();
        return 1;
    }

    private static void PrintHelp()
    {
        Console.WriteLine(
            """
            WitcherScript REDkit Tooling CLI

            Commands:
              detect
              init
              print-config
              validate
              recompile --executable <path>
              launch-game [--executable <path>] [-- <args>]

            Common options:
              --project-dir <path>
              --game-dir <path>
              --redkit-dir <path>
              --force
              --json
            """
        );
    }

    private sealed record CommandOptions(
        string? ProjectDirectory,
        string? GameDirectory,
        string? RedkitDirectory,
        string? Executable,
        bool Force,
        bool Json,
        IReadOnlyList<string> Arguments
    )
    {
        public DetectionOptions ToDetectionOptions()
        {
            return new DetectionOptions(ProjectDirectory, GameDirectory, RedkitDirectory);
        }

        public static CommandOptions Parse(string[] args)
        {
            string? projectDirectory = null;
            string? gameDirectory = null;
            string? redkitDirectory = null;
            string? executable = null;
            var force = false;
            var json = false;
            var passThrough = new List<string>();

            for (var index = 0; index < args.Length; index++)
            {
                var arg = args[index];
                if (arg == "--")
                {
                    passThrough.AddRange(args[(index + 1)..]);
                    break;
                }

                switch (arg)
                {
                    case "--project-dir":
                        projectDirectory = ReadValue(args, ref index, arg);
                        break;
                    case "--game-dir":
                        gameDirectory = ReadValue(args, ref index, arg);
                        break;
                    case "--redkit-dir":
                        redkitDirectory = ReadValue(args, ref index, arg);
                        break;
                    case "--executable":
                        executable = ReadValue(args, ref index, arg);
                        break;
                    case "--force":
                        force = true;
                        break;
                    case "--json":
                        json = true;
                        break;
                    default:
                        passThrough.Add(arg);
                        break;
                }
            }

            return new CommandOptions(
                projectDirectory,
                gameDirectory,
                redkitDirectory,
                executable,
                force,
                json,
                passThrough
            );
        }

        private static string ReadValue(string[] args, ref int index, string option)
        {
            if (index + 1 >= args.Length)
            {
                throw new ArgumentException($"Missing value for option: {option}");
            }

            index++;
            return args[index];
        }
    }
}
