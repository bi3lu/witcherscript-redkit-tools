statemachine class W3WitchesCage extends CEntity
{
    default autoState = 'TurnedOff';
}

state TurnedOn in W3WitchesCage
{
    event OnEnterState(prevStateName : name)
    {
        super.OnEnterState(prevStateName);
        parent.ApplyAppearance("roots_on");
    }
}

exec function acquire(skillName : name)
{
    var skills : array< int >;
    thePlayer.DisplayHudMessage('Hello');
}

latent storyscene function ShaveGeralt(player : CStoryScenePlayer)
{
    Sleep(1.0f);
}

timer function Loop(dt : float, id : int)
{
    LoopFunction(dt);
}

quest function LaunchCredits()
{
    theGame.GetGuiManager().RequestCreditsMenu(CreditsIndex_Witcher3);
}

cleanup function ThrowProjectileCleanup()
{
    if (parent.wasBombReleased == false)
    {
        parent.wasBombReleased = true;
    }
}

import class CScriptableState extends IScriptable
{
    import final function AddTimer(timerName : name, period : float, optional repeats : bool) : int;
}
