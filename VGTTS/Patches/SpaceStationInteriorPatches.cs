using System.Diagnostics;
using System.Threading.Tasks;
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
            var sw = Stopwatch.StartNew();

            // 1. CheckUpdatePatrons rolls new patrons once per in-game day.
            //    On same-day re-entry this is a no-op (patrons came from save).
            bar.CheckUpdatePatrons();

            // 2. Regardless of whether step 1 rolled new ones, ensure every
            //    patron has had Initialize() called. Save-restored patrons
            //    are still un-initialized (initialized=false, dialogueLines
            //    null for Salesman) until something triggers it — the game
            //    normally does this lazily in BarUI at bar-open time. By
            //    calling Initialize here we flip our warm trigger from
            //    bar-open to station-dock for same-day re-entries.
            //    Initialize is idempotent via its own !initialized guard.
            foreach (var patron in bar.availablePatrons) patron.Initialize();

            Plugin.Log.LogDebug(
                $"[station-warm] Initialized {bar.availablePatrons.Count} bar patron(s) on dock");

            var pending = BarPatronPatches.DrainPendingWarms();
            if (pending.Count == 0)
            {
                Plugin.Log.LogDebug(
                    $"[station-warm] No new warm tasks (all cached); setup took {sw.ElapsedMilliseconds}ms");
                return;
            }
            _ = Task.Run(async () =>
            {
                await Task.WhenAll(pending).ConfigureAwait(false);
                Plugin.Log.LogDebug(
                    $"[station-warm] All {pending.Count} bar warm task(s) finished in {sw.ElapsedMilliseconds}ms");
            });
        }
        catch (System.Exception ex)
        {
            Plugin.Log.LogWarning($"[station-warm] Bar pre-populate failed: {ex.Message}");
        }
    }
}
