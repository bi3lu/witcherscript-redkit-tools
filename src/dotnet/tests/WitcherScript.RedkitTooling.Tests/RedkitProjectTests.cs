using Xunit;

namespace WitcherScript.RedkitTooling.Tests;

public sealed class RedkitProjectTests
{
    [Fact]
    public void ProjectModelStoresScriptRoots()
    {
        var project = new RedkitProject(
            "Sample",
            "D:/REDkitProjects/Sample",
            null,
            null,
            [],
            ["D:/REDkitProjects/Sample/content/scripts"]
        );

        Assert.Equal("Sample", project.Name);
        Assert.Single(project.ScriptRoots);
    }

    [Fact]
    public void ProjectDetectorFindsRepositoriesAndScriptRoots()
    {
        using var workspace = TemporaryWorkspace.Create();
        var projectContentScripts = workspace.CreateDirectory(
            "Project",
            "content",
            "scripts"
        );
        var vanillaScripts = workspace.CreateDirectory(
            "Game",
            "content",
            "content0",
            "scripts"
        );
        var dlcScripts = workspace.CreateDirectory(
            "Game",
            "dlc",
            "dlcOne",
            "content",
            "scripts"
        );
        workspace.CreateFile("Game", "bin", "x64", "witcher3.exe");
        workspace.CreateFile("REDkit", "REDkit.exe");

        var detector = new RedkitProjectDetector();
        var project = detector.Detect(
            new DetectionOptions(
                workspace.PathFor("Project"),
                workspace.PathFor("Game"),
                workspace.PathFor("REDkit")
            )
        );

        Assert.Equal("Project", project.Name);
        Assert.Equal(workspace.PathFor("Game"), project.GameDirectory);
        Assert.Equal(workspace.PathFor("REDkit"), project.RedkitDirectory);
        Assert.Contains(projectContentScripts, project.ScriptRoots);
        Assert.Contains(vanillaScripts, project.ScriptRoots);
        Assert.Contains(dlcScripts, project.ScriptRoots);
        Assert.Contains(project.ContentRepositories, repository => repository.Kind == ContentRepositoryKind.Project);
        Assert.Contains(project.ContentRepositories, repository => repository.Kind == ContentRepositoryKind.Vanilla);
        Assert.Contains(project.ContentRepositories, repository => repository.Kind == ContentRepositoryKind.Dlc);
    }

    [Fact]
    public void ConfigWriterExportsLanguageServerConfiguration()
    {
        using var workspace = TemporaryWorkspace.Create();
        var projectScripts = workspace.CreateDirectory("Project", "content", "scripts");
        var vanillaScripts = workspace.CreateDirectory("Game", "content", "content0", "scripts");
        var project = new RedkitProject(
            "Sample",
            workspace.PathFor("Project"),
            workspace.PathFor("Game"),
            workspace.PathFor("REDkit"),
            [
                new ContentRepository(
                    "project",
                    workspace.PathFor("Project", "content"),
                    ContentRepositoryKind.Project,
                    0
                ),
                new ContentRepository(
                    "vanilla",
                    workspace.PathFor("Game", "content", "content0"),
                    ContentRepositoryKind.Vanilla,
                    1
                ),
            ],
            [projectScripts, vanillaScripts]
        );

        var toml = new WitcherScriptConfigWriter().Write(project);

        Assert.Contains("[project]", toml, StringComparison.Ordinal);
        Assert.Contains("name = \"Sample\"", toml, StringComparison.Ordinal);
        Assert.Contains(
            projectScripts.Replace("\\", "\\\\", StringComparison.Ordinal),
            toml,
            StringComparison.Ordinal
        );
        Assert.Contains(
            vanillaScripts.Replace("\\", "\\\\", StringComparison.Ordinal),
            toml,
            StringComparison.Ordinal
        );
    }

    [Fact]
    public void ValidatorReportsMissingScriptRoots()
    {
        using var workspace = TemporaryWorkspace.Create();
        var project = new RedkitProject(
            "Broken",
            workspace.PathFor("Project"),
            null,
            null,
            [],
            []
        );

        var report = new RedkitProjectValidator().Validate(project);

        Assert.False(report.IsValid);
        Assert.Contains(report.Messages, message => message.Code == "WS5004");
    }

    [Fact]
    public async Task ScriptCompilerRunnerUsesProjectWorkingDirectory()
    {
        var runner = new RecordingProcessRunner();
        var project = new RedkitProject("Sample", "/project", null, null, [], []);

        await new ScriptCompilerRunner(runner).RecompileAsync(
            project,
            "/tools/recompile",
            TestContext.Current.CancellationToken
        );

        Assert.Equal("/tools/recompile", runner.FileName);
        Assert.Equal(["recompile", "--project", "/project"], runner.Arguments);
        Assert.Equal("/project", runner.WorkingDirectory);
    }

    [Fact]
    public async Task GameLauncherUsesGameDirectoryAsWorkingDirectory()
    {
        var runner = new RecordingProcessRunner();
        var project = new RedkitProject("Sample", "/project", "/game", null, [], []);

        await new GameLauncher(runner).LaunchAsync(
            project,
            "/game/bin/x64/witcher3.exe",
            ["-debug"],
            TestContext.Current.CancellationToken
        );

        Assert.Equal("/game/bin/x64/witcher3.exe", runner.FileName);
        Assert.Equal(["-debug"], runner.Arguments);
        Assert.Equal("/game", runner.WorkingDirectory);
    }

    private sealed class RecordingProcessRunner : IProcessRunner
    {
        public string? FileName { get; private set; }
        public IReadOnlyList<string> Arguments { get; private set; } = [];
        public string? WorkingDirectory { get; private set; }

        public Task<ProcessRunResult> RunAsync(
            string fileName,
            IReadOnlyList<string> arguments,
            string? workingDirectory,
            CancellationToken cancellationToken = default
        )
        {
            FileName = fileName;
            Arguments = arguments;
            WorkingDirectory = workingDirectory;
            return Task.FromResult(new ProcessRunResult(0, string.Empty, string.Empty));
        }
    }

    private sealed class TemporaryWorkspace : IDisposable
    {
        private readonly string _root = System.IO.Path.Combine(
            System.IO.Path.GetTempPath(),
            System.IO.Path.GetRandomFileName()
        );

        private TemporaryWorkspace()
        {
            Directory.CreateDirectory(_root);
        }

        public static TemporaryWorkspace Create()
        {
            return new TemporaryWorkspace();
        }

        public string PathFor(params string[] parts)
        {
            return System.IO.Path.GetFullPath(System.IO.Path.Combine([_root, .. parts]));
        }

        public string CreateDirectory(params string[] parts)
        {
            var path = PathFor(parts);
            Directory.CreateDirectory(path);
            return path;
        }

        public void CreateFile(params string[] parts)
        {
            var path = PathFor(parts);
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path)!);
            File.WriteAllText(path, string.Empty);
        }

        public void Dispose()
        {
            if (Directory.Exists(_root))
            {
                Directory.Delete(_root, recursive: true);
            }
        }
    }
}
