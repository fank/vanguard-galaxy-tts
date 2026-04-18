using Behaviour.UI.HUD;
using HarmonyLib;

namespace VGTTS.Patches;

/// <summary>
/// Hook on <see cref="HudManager.SetEchoRemarksStatus"/> — the game calls this
/// with <c>active=true</c> the moment a travel leg begins (from TravelManager.
/// Travel coroutine), and <c>active=false</c> when it ends or cancels.
/// We use it to record the travel start time so <see cref="EchoTipFilter"/>
/// can suppress hints during the first N seconds of short hops.
/// </summary>
[HarmonyPatch(typeof(HudManager))]
internal static class HudManagerPatches
{
    [HarmonyPrefix]
    [HarmonyPatch(nameof(HudManager.SetEchoRemarksStatus))]
    private static void SetEchoRemarksStatus_Prefix(bool active)
    {
        if (active) EchoTipFilter.OnTravelStart();
    }
}
