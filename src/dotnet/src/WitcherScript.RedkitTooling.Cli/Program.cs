namespace WitcherScript.RedkitTooling.Cli;

internal static class Program
{
    private static int Main(string[] args)
    {
        if (args is ["--version"] or ["version"])
        {
            Console.WriteLine("ws-redkit 0.1.0");
            return 0;
        }

        Console.WriteLine("WitcherScript REDkit Tooling CLI");
        return 0;
    }
}
