import "vanilla_like/combat_actor";

class RedkitPreviewTool
{
    var selectedActor : PlayerActor;

    function PreviewDamage(amount : float) : float
    {
        return selectedActor.ApplyDamage(amount);
    }

    event OnSelectionChanged(actor : PlayerActor)
    {
        selectedActor = actor;
    }
}
