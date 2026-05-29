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
}
