using System.Text;

namespace WitcherScript.RedkitTooling;

/// <summary>
/// Writes language-server compatible <c>witcherscript.toml</c> configuration files.
/// </summary>
public sealed class WitcherScriptConfigWriter
{
    /// <summary>
    /// Serializes a REDkit project model to TOML understood by the language server.
    /// </summary>
    /// <param name="project">Project model to serialize.</param>
    /// <returns>The generated TOML document.</returns>
    public string Write(RedkitProject project)
    {
        var builder = new StringBuilder();

        builder.AppendLine("[project]");
        builder.Append("name = ");
        builder.AppendLine(Quote(project.Name));
        builder.AppendLine();

        builder.AppendLine("[redkit]");
        AppendNullablePath(builder, "game_directory", project.GameDirectory);
        AppendNullablePath(builder, "redkit_directory", project.RedkitDirectory);
        AppendNullablePath(builder, "project_directory", project.ProjectDirectory);
        builder.AppendLine();

        builder.AppendLine("[scripts]");
        AppendArray(builder, "source_roots", ProjectScriptRoots(project));
        AppendArray(builder, "vanilla_roots", VanillaScriptRoots(project));
        AppendArray(builder, "exclude", ["**/bin/**", "**/.cache/**", "**/.ws-cache/**", "**/generated/**"]);

        return builder.ToString();
    }

    /// <summary>
    /// Writes a language-server configuration file to disk.
    /// </summary>
    /// <param name="project">Project model to serialize.</param>
    /// <param name="path">Destination file path.</param>
    /// <param name="overwrite">Whether an existing file may be replaced.</param>
    public ConfigWriteResult WriteToFile(RedkitProject project, string path, bool overwrite)
    {
        var existed = File.Exists(path);
        if (File.Exists(path) && !overwrite)
        {
            throw new IOException($"Configuration file already exists: {path}. Use --force to overwrite it.");
        }

        var backupPath = existed ? $"{path}.bak" : null;
        if (backupPath is not null)
        {
            File.Copy(path, backupPath, overwrite: true);
        }

        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrWhiteSpace(directory))
        {
            Directory.CreateDirectory(directory);
        }

        var temporaryPath = $"{path}.tmp";
        File.WriteAllText(temporaryPath, Write(project), Encoding.UTF8);
        File.Move(temporaryPath, path, overwrite: true);

        return new ConfigWriteResult(path, existed, backupPath);
    }

    private static string[] ProjectScriptRoots(RedkitProject project)
    {
        return
        [
            .. project.ScriptRoots.Where(root =>
                project.ContentRepositories.Any(repository =>
                    repository.Kind == ContentRepositoryKind.Project
                    && root.StartsWith(repository.Path, StringComparison.OrdinalIgnoreCase)
                )
            ),
        ];
    }

    private static string[] VanillaScriptRoots(RedkitProject project)
    {
        return
        [
            .. project.ScriptRoots.Where(root =>
                project.ContentRepositories.Any(repository =>
                    repository.Kind != ContentRepositoryKind.Project
                    && root.StartsWith(repository.Path, StringComparison.OrdinalIgnoreCase)
                )
            ),
        ];
    }

    private static void AppendNullablePath(StringBuilder builder, string key, string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return;
        }

        builder.Append(key);
        builder.Append(" = ");
        builder.AppendLine(Quote(value));
    }

    private static void AppendArray(StringBuilder builder, string key, IEnumerable<string> values)
    {
        builder.Append(key);
        builder.AppendLine(" = [");

        foreach (var value in values)
        {
            builder.Append("  ");
            builder.Append(Quote(value));
            builder.AppendLine(",");
        }

        builder.AppendLine("]");
        builder.AppendLine();
    }

    private static string Quote(string value)
    {
        return $"\"{value.Replace("\\", "\\\\", StringComparison.Ordinal).Replace("\"", "\\\"", StringComparison.Ordinal)}\"";
    }
}

/// <summary>
/// Describes the result of writing a language-server configuration file.
/// </summary>
/// <param name="Path">Destination configuration path.</param>
/// <param name="OverwroteExistingFile">Whether an existing file was replaced.</param>
/// <param name="BackupPath">Backup path created before replacing an existing file.</param>
public sealed record ConfigWriteResult(
    string Path,
    bool OverwroteExistingFile,
    string? BackupPath
);
