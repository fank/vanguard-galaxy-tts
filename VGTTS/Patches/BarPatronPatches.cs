using System.Collections.Generic;
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
