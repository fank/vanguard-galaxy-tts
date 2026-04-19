using System.Collections.Generic;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Threading.Tasks;
using HarmonyLib;
using Source.Dialogues;
using Source.Galaxy.POI.Station;
using Source.Galaxy.POI.Station.Patrons;
using VGTTS.Audio;
using VGTTS.Text;

namespace VGTTS.Patches;

/// <summary>
/// Pre-warms the TTS cache for space-station bar patrons — salesmen + crew
/// recruiters — as soon as they're initialized, well before the player walks
/// in to interact.
///
/// Both patron types are procedurally named:
///   Salesman:   random firstName + 1 of 4 dialogue variants, fully resolved
///               at Salesman.InitializeData() time (stored in private
///               dialogueLines field). Caller: Bar.CreateBarPatron().
///   CrewMember: random CrewMemberData, fixed 1-line dialogue built on the
///               fly in InteractWithPatron() using crewMember.firstName.
///
/// Bar.CreateBarPatron creates N patrons per station, each gets
/// <c>BarPatron.Initialize()</c> called right after construction. That's our
/// hook: fires once, at which point both Salesman's dialogueLines and
/// CrewMember's crewMember are fully populated.
/// </summary>
[HarmonyPatch(typeof(BarPatron))]
internal static class BarPatronPatches
{
    private const string CrewRecruitLine = "Heya, heard you're looking for crew?";

    /// <summary>Per-patron record of the (speaker, text) pairs we warmed.
    /// ConditionalWeakTable so the entries GC when the BarPatron does.</summary>
    private static readonly ConditionalWeakTable<BarPatron, List<(string Speaker, string Text)>> _patronLines = new();

    /// <summary>Internal accessor for BarRefreshPatches — hands over the warmed
    /// lines for a patron about to go out of scope so they can be evicted.</summary>
    internal static bool TryTakeLines(BarPatron patron, out List<(string Speaker, string Text)> lines)
    {
        if (_patronLines.TryGetValue(patron, out lines))
        {
            _patronLines.Remove(patron);
            return true;
        }
        lines = null!;
        return false;
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(BarPatron.Initialize))]
    private static void Initialize_Postfix(BarPatron __instance)
    {
        var controller = TtsController.Instance;
        if (controller == null) return;
        if (Plugin.Instance == null || !Plugin.Instance.CfgEnabled.Value || !Plugin.Instance.CfgDialogue.Value) return;

        var pairs = new List<(string Speaker, string Text)>();
        switch (__instance)
        {
            case Salesman salesman:
                // Private field: dialogueLines. Traverse the fully-resolved list —
                // covers all 4 SalesmanXxx variants without caring which rolled.
                var lines = Traverse.Create(salesman).Field<List<DialogueLine>>("dialogueLines").Value;
                if (lines == null) return;
                var salesmanName = salesman.name;
                foreach (var line in lines)
                {
                    if (string.IsNullOrWhiteSpace(line?.text)) continue;
                    var speaker = line.character == Characters.captain
                        ? ResolveCaptainSpeaker()
                        : (line.character?.name ?? salesmanName);
                    pairs.Add((speaker, line.text));
                }
                break;

            case CrewMember crew when crew.crewMember != null:
                // Dialogue is hardcoded in CrewMember.InteractWithPatron; we know
                // it upfront so pre-warm it with the current crewMember's firstName.
                pairs.Add((crew.crewMember.firstName, CrewRecruitLine));
                break;

            default:
                return;
        }

        if (pairs.Count == 0) return;

        _patronLines.AddOrUpdate(__instance, pairs);

        _ = Task.Run(async () =>
        {
            foreach (var (speaker, text) in pairs)
            {
                try
                {
                    await controller.WarmCacheAsync(speaker, TextNormalizer.ForTts(text), CancellationToken.None)
                        .ConfigureAwait(false);
                }
                catch { /* best-effort; StartDialogue fallback warms again on click */ }
            }
        });
    }

    /// <summary>Mirror of DialogueManagerPatches.ResolveCaptainPreset — but we
    /// can't call private static from here, so resolve locally.</summary>
    private static string ResolveCaptainSpeaker()
    {
        var cfg = Plugin.Instance.CfgCaptainPreset.Value?.ToLowerInvariant() ?? "auto";
        if (cfg is "m1" or "m2" or "m3" or "f1" or "f2" or "f3") return "captain_" + cfg;
        var isFemale = Source.Player.GamePlayer.current?.commander?.gender == Source.Crew.Gender.Female;
        return isFemale ? "captain_f1" : "captain_m1";
    }
}

/// <summary>
/// Evicts procedural-patron WAVs from the session cache when a bar refreshes
/// its roster (the game does this once per in-game day, wiping the old 5
/// patrons and rolling 5 new ones). Without this, the session cache carries
/// every patron the player has ever seen in any bar today.
///
/// Hooks <c>Bar.CheckUpdatePatrons</c> as prefix+postfix. The prefix snapshots
/// the current availablePatrons; the postfix diffs against the new list and
/// drops cache entries for any patron that left.
/// </summary>
[HarmonyPatch(typeof(Bar))]
internal static class BarRefreshPatches
{
    private static readonly ConditionalWeakTable<Bar, List<BarPatron>> _snapshots = new();

    [HarmonyPrefix]
    [HarmonyPatch(nameof(Bar.CheckUpdatePatrons))]
    private static void CheckUpdatePatrons_Prefix(Bar __instance)
    {
        _snapshots.AddOrUpdate(__instance, new List<BarPatron>(__instance.availablePatrons));
    }

    [HarmonyPostfix]
    [HarmonyPatch(nameof(Bar.CheckUpdatePatrons))]
    private static void CheckUpdatePatrons_Postfix(Bar __instance)
    {
        if (!_snapshots.TryGetValue(__instance, out var before)) return;
        _snapshots.Remove(__instance);

        var controller = TtsController.Instance;
        if (controller == null) return;

        var after = new HashSet<BarPatron>(__instance.availablePatrons);
        foreach (var patron in before)
        {
            if (after.Contains(patron)) continue;
            // Patron rolled off the roster — drop its warmed audio
            if (BarPatronPatches.TryTakeLines(patron, out var lines))
            {
                foreach (var (speaker, text) in lines)
                    controller.DropCache(speaker, text);
            }
        }
    }
}
