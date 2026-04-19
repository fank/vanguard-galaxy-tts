using HarmonyLib;
using Source.Galaxy.POI;

namespace VGTTS.Patches;

/// <summary>
/// Triggers bar-patron initialization the moment the player docks at a
/// space station — before they've even navigated to the bar UI.
///
/// The game normally generates/refreshes bar patrons lazily: BarUI.Start
/// calls <c>bar.CheckUpdatePatrons()</c>, which rolls 5 new patrons once
/// per in-game day and <c>Initialize()</c>s each. Our
/// <see cref="BarPatronPatches"/> hook fires on that Initialize call,
/// starting the warm synth.
///
/// Problem: that whole chain only runs when the player actually opens
/// the bar menu, giving us ~1-2 seconds before they click a patron —
/// often not enough for sherpa-onnx to finish the synth.
///
/// Fix: <c>SpaceStationInterior.Start</c> runs when the interior scene
/// loads (player has just docked). We call <c>CheckUpdatePatrons()</c>
/// here too — the method is day-gated so it's a no-op on re-entry,
/// otherwise it rolls + initializes patrons NOW instead of at bar open.
/// BarUI later calls the same method again; second call is no-op because
/// the day didn't change.
///
/// Net effect: bar-warm synth starts during the docking animation,
/// typically 5-30 seconds of buffer before the player clicks anyone.
/// </summary>
[HarmonyPatch(typeof(Behaviour.UI.Spacestation.SpaceStationInterior))]
internal static class SpaceStationInteriorPatches
{
    [HarmonyPostfix]
    [HarmonyPatch("Start")]
    private static void Start_Postfix()
    {
        var bar = SpaceStation.current?.bar;
        if (bar == null) return;
        try
        {
            bar.CheckUpdatePatrons();
            Plugin.Log.LogInfo($"[station-warm] Pre-populated bar patrons on dock — {bar.availablePatrons.Count} patron(s)");
        }
        catch (System.Exception ex)
        {
            Plugin.Log.LogWarning($"[station-warm] Bar pre-populate failed: {ex.Message}");
        }
    }
}
