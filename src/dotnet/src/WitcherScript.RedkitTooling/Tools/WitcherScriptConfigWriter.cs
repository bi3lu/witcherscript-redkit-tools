using System.Text;

namespace WitcherScript.RedkitTooling;

public sealed class WitcherScriptConfigWriter
{
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

    public void WriteToFile(RedkitProject project, string path, bool overwrite)
    {
        if (File.Exists(path) && !overwrite)
        {
            throw new IOException($"Configuration file already exists: {path}");
        }

        File.WriteAllText(path, Write(project), Encoding.UTF8);
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
