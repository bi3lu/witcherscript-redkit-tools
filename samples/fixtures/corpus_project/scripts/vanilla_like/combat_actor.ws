class CActor
{
    var displayName : string;
    var health : float;

    function ApplyDamage(amount : float) : float
    {
        var remaining : float = health - amount;
        health = remaining;
        return health;
    }
}

class PlayerActor extends CActor
{
    var level : int;

    function IsAlive() : bool
    {
        return health > 0.0f;
    }
}
