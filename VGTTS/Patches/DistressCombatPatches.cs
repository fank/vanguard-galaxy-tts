using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using HarmonyLib;
using Source.Data;
using Source.SpaceShip;
using VGTTS.Audio;
using VGTTS.Text;

namespace VGTTS.Patches;

/// <summary>
/// Pre-warms the rescue dialogue for distress-combat encounters during the
/// combat itself, before the dialogue even triggers.
///
/// The encounter works like this (Source.Simulation.World.POI.DistressCombat):
///   1. Player enters the POI, combat starts, friendly ship + pirates spawn
///   2. Player kills pirates
///   3. Game ticks UpdateActive every frame — checks for no-more-enemies
///      and spawns the 3-line rescue dialogue
///
/// The friendly ship's commanderData.firstName is known from step 1 onward,
/// and it becomes the DialogueLine speaker for 2 of the 3 lines. Without
/// warm-up those lines hit live-TTS on first utterance (~1s delay) because
/// the procedural name is never in the prerender pack.
///
/// This patch spots the encounter on the first UpdateActive tick where a
/// friendly ship is present, and fires a background task to warm both
/// procedural lines. By the time the player finishes combat, the WAVs are
/// in DiskCache and the dialogue plays instantly.
///
/// Captain's reply line comes from DefaultVoiceMap + the captain preset
/// warm on save load, so it's already covered.
/// </summary>
[HarmonyPatch(typeof(Source.Simulation.World.POI.DistressCombat))]
internal static class DistressCombatPatches
{
    // Guard against re-warming every frame — UpdateActive fires ~60Hz during
    // combat. Keyed by the storyteller instance (GC'd when the encounter ends).
    private static readonly HashSet<Source.Simulation.World.POI.DistressCombat> _warmed = new();
    private static readonly object _warmedLock = new();

    private const string LineRescued =
        "Phew, that was a close call! Those pirates disabled our warp drive, they would've had us for lunch! Thanks for the help!";
    private const string LineReward =
        "Err, yes, of course. Here you go.";

    [HarmonyPrefix]
    [HarmonyPatch(nameof(Source.Simulation.World.POI.DistressCombat.UpdateActive))]
    private static void UpdateActive_Prefix(Source.Simulation.World.POI.DistressCombat __instance)
    {
        if (__instance == null || __instance.rewardClaimed) return;
        lock (_warmedLock)
        {
            if (_warmed.Contains(__instance)) return;
        }

        var controller = TtsController.Instance;
        if (controller == null) return;
        if (Plugin.Instance == null || !Plugin.Instance.CfgEnabled.Value || !Plugin.Instance.CfgDialogue.Value) return;

        // Find the friendly ship — same iteration the game uses to spot a
        // rescue-target candidate. If none spawned yet, we'll retry next tick.
        string? friendName = null;
        foreach (AbstractUnitData unit in __instance.poi.GetUnits())
        {
            if (unit.IsPlayerEnemy()) continue;
            if (unit is SpaceShipData ship && ship.commanderData != null)
            {
                friendName = ship.commanderData.firstName;
                break;
            }
        }
        if (string.IsNullOrEmpty(friendName)) return;

        lock (_warmedLock) _warmed.Add(__instance);

        Plugin.Log.LogInfo($"[distress-warm] Pre-warming rescue dialogue for '{friendName}' during combat");
        _ = Task.Run(async () =>
        {
            foreach (var line in new[] { LineRescued, LineReward })
            {
                try
                {
                    await controller.WarmCacheAsync(friendName!, TextNormalizer.ForTts(line), CancellationToken.None)
                        .ConfigureAwait(false);
                }
                catch { /* best-effort; StartDialogue hook will retry on-demand */ }
            }
        });
    }
}
