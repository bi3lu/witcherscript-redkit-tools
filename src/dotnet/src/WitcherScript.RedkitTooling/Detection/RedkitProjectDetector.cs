namespace WitcherScript.RedkitTooling;

public sealed class RedkitProjectDetector
{
    private readonly GameInstallationDetector _gameDetector;
    private readonly RedkitInstallationDetector _redkitDetector;

    public RedkitProjectDetector(
        GameInstallationDetector? gameDetector = null,
        RedkitInstallationDetector? redkitDetector = null
    )
    {
        _gameDetector = gameDetector ?? new GameInstallationDetector();
        _redkitDetector = redkitDetector ?? new RedkitInstallationDetector();
    }

    public RedkitProject Detect(DetectionOptions options)
    {
        var projectDirectory = ResolveProjectDirectory(options.ProjectDirectory);
        var gameDirectory = _gameDetector.Detect(options.GameDirectory);
        var redkitDirectory = _redkitDetector.Detect(options.RedkitDirectory);
        var repositories = DetectContentRepositories(projectDirectory, gameDirectory);
        var scriptRoots = repositories
            .Select(repository => Path.Combine(repository.Path, "scripts"))
            .Where(Directory.Exists)
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToArray();

        return new RedkitProject(
            Path.GetFileName(projectDirectory),
            projectDirectory,
            gameDirectory,
            redkitDirectory,
            repositories,
            scriptRoots
        );
    }

    public ToolDetectionResult DetectResult(DetectionOptions options)
    {
        var project = Detect(options);
        return new ToolDetectionResult(
            project.GameDirectory,
            project.RedkitDirectory,
            project.ProjectDirectory,
            project.ScriptRoots
        );
    }

    private static string ResolveProjectDirectory(string? projectDirectory)
    {
        var path = string.IsNullOrWhiteSpace(projectDirectory)
            ? Environment.CurrentDirectory
            : projectDirectory;

        return Path.GetFullPath(path);
    }

    private static ContentRepository[] DetectContentRepositories(
        string projectDirectory,
        string? gameDirectory
    )
    {
        var repositories = new List<ContentRepository>();
        var loadOrder = 0;

        AddIfExists(
            repositories,
            "project",
            Path.Combine(projectDirectory, "content"),
            ContentRepositoryKind.Project,
            loadOrder++
        );
        AddIfExists(repositories, "project", projectDirectory, ContentRepositoryKind.Project, loadOrder++);

        if (!string.IsNullOrWhiteSpace(gameDirectory))
        {
            AddIfExists(
                repositories,
                "vanilla",
                Path.Combine(gameDirectory, "content", "content0"),
                ContentRepositoryKind.Vanilla,
                loadOrder++
            );
            loadOrder = AddRepositoryGroup(
                repositories,
                Path.Combine(gameDirectory, "dlc"),
                ContentRepositoryKind.Dlc,
                loadOrder
            );
            _ = AddRepositoryGroup(
                repositories,
                Path.Combine(gameDirectory, "Mods"),
                ContentRepositoryKind.Mod,
                loadOrder
            );
        }

        return [.. repositories.DistinctBy(repository => repository.Path)];
    }

    private static int AddRepositoryGroup(
        List<ContentRepository> repositories,
        string root,
        ContentRepositoryKind kind,
        int loadOrder
    )
    {
        if (!Directory.Exists(root))
        {
            return loadOrder;
        }

        foreach (var directory in Directory.GetDirectories(root).Order(StringComparer.OrdinalIgnoreCase))
        {
            var contentDirectory = Path.Combine(directory, "content");
            
            if (!Directory.Exists(contentDirectory))
            {
                continue;
            }

            repositories.Add(
                new ContentRepository(
                    Path.GetFileName(directory),
                    Path.GetFullPath(contentDirectory),
                    kind,
                    loadOrder++
                )
            );
        }

        return loadOrder;
    }

    private static void AddIfExists(
        List<ContentRepository> repositories,
        string name,
        string path,
        ContentRepositoryKind kind,
        int loadOrder
    )
    {
        if (!Directory.Exists(path))
        {
            return;
        }

        repositories.Add(new ContentRepository(name, Path.GetFullPath(path), kind, loadOrder));
    }
}
