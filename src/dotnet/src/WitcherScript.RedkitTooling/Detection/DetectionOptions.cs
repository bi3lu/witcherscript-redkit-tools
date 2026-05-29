namespace WitcherScript.RedkitTooling;

public sealed record DetectionOptions(
    string? ProjectDirectory = null,
    string? GameDirectory = null,
    string? RedkitDirectory = null
);
