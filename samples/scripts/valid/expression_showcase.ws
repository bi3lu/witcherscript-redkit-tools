class ExpressionShowcase
{
    var title : string = "wolf";
    var count : int = 1 + 2 * 3;

    function run(player : Player) : int
    {
        var index : int = 0;
        index = index + 1;
        player.inventory.GetItem(index).name;
        return !(index > 3) && player.items[index] != none;
    }
}
