using HarmonyLib;
using Source.Dialogues;
using VGTTS.Prerender;

namespace VGTTS.Patches;

/// <summary>
/// Patch on <see cref="Characters.CreateCaptain"/> — fires once per new-game /
/// save-load when the player captain Character is built from the commander's
/// callsign (or firstName if no callsign is set). This is the earliest point
/// where <c>captain.name</c> is known, so we use it to kick off background
/// warming of the DiskCache for all captain.name dialogue lines.
/// </summary>
[HarmonyPatch(typeof(Characters))]
internal static class CharactersPatches
{
    [HarmonyPostfix]
    [HarmonyPatch(nameof(Characters.CreateCaptain))]
    private static void CreateCaptain_Postfix()
    {
        var captain = Characters.captain;
        if (captain == null || string.IsNullOrEmpty(captain.name)) return;
        CaptainNameCache.WarmInBackground(captain.name);
    }
}
