import "redkit_like/editor_tool";

class ModBuff
{
    var owner : PlayerActor;
    var stackCount : int = 1;

    function Apply(tool : RedkitPreviewTool) : bool
    {
        var preview : float = tool.PreviewDamage(5.0f);
        stackCount = stackCount + 1;
        return owner.IsAlive() && preview >= 0.0f;
    }
}
