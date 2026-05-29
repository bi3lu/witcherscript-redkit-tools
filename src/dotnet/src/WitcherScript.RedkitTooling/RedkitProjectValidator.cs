namespace WitcherScript.RedkitTooling;

public sealed class RedkitProjectValidator
{
    public ValidationReport Validate(RedkitProject project)
    {
        var messages = new List<ValidationMessage>();

        AddDirectoryMessage(messages, "WS5001", "Project directory", project.ProjectDirectory, required: true);
        AddDirectoryMessage(messages, "WS5002", "Game directory", project.GameDirectory, required: false);
        AddDirectoryMessage(messages, "WS5003", "REDkit directory", project.RedkitDirectory, required: false);

        if (project.ScriptRoots.Count == 0)
        {
            messages.Add(
                new ValidationMessage(
                    ValidationSeverity.Error,
                    "WS5004",
                    "No WitcherScript roots were detected."
                )
            );
        }

        foreach (var scriptRoot in project.ScriptRoots)
        {
            AddDirectoryMessage(messages, "WS5005", "Script root", scriptRoot, required: true);
        }

        return new ValidationReport(messages);
    }

    private static void AddDirectoryMessage(
        List<ValidationMessage> messages,
        string code,
        string label,
        string? path,
        bool required
    )
    {
        if (string.IsNullOrWhiteSpace(path))
        {
            if (required)
            {
                messages.Add(
                    new ValidationMessage(
                        ValidationSeverity.Error,
                        code,
                        $"{label} is not configured."
                    )
                );
            }

            return;
        }

        messages.Add(
            Directory.Exists(path)
                ? new ValidationMessage(ValidationSeverity.Info, code, $"{label} exists.", path)
                : new ValidationMessage(ValidationSeverity.Error, code, $"{label} does not exist.", path)
        );
    }
}
