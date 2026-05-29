import "game/scripts/player.ws";

class PlayerSample extends Actor
{
    // Line comment
    var health : float = 100.0f;
    var name : string = "Geralt \"White Wolf\"";

    /* Block
       comment */
    function Heal(amount : int) : void
    {
        if (amount >= 0 && health < 100.0)
        {
            health += amount;
            return;
        }
    }
}
