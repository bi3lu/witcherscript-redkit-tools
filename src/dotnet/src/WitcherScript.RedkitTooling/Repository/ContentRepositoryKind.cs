namespace WitcherScript.RedkitTooling;

/// <summary>
/// Identifies the role of a content repository in script and asset discovery.
/// </summary>
public enum ContentRepositoryKind
{
    /// <summary>
    /// Base game content repository.
    /// </summary>
    Vanilla,

    /// <summary>
    /// Downloadable content repository.
    /// </summary>
    Dlc,

    /// <summary>
    /// Installed mod repository.
    /// </summary>
    Mod,

    /// <summary>
    /// Active REDkit project repository.
    /// </summary>
    Project
}
