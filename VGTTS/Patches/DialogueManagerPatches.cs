using System.Collections.Generic;
using Behaviour.Dialogues;
using HarmonyLib;
using Source.Crew;
using Source.Dialogues;
using Source.Player;
using VGTTS.Audio;

namespace VGTTS.Patches;

/// <summary>
/// Patches on <see cref="DialogueManager"/>:
///   • Prefix on <c>ShowDialogueLine</c> — synth each line as it appears. Advancing
///     past the previous line naturally routes through here again, and <c>Speak</c>
///     interrupts whatever was playing.
///   • Prefix on <c>CloseDialogue</c> — stop audio when the dialogue window closes
///     (escape / click-close / natural end-of-conversation).
/// </summary>
[HarmonyPatch(typeof(DialogueManager))]
internal static class DialogueManagerPatches
{
    [HarmonyPrefix]
    [HarmonyPatch("ShowDialogueLine")]
    private static void ShowDialogueLine_Prefix(
        List<DialogueLine> ___dialogue,
        int ___currentLineIndex)
    {
        if (___dialogue == null || ___currentLineIndex < 0 || ___currentLineIndex >= ___dialogue.Count)
            return;

        var line = ___dialogue[___currentLineIndex];
        var text = line?.text ?? string.Empty;
        var speaker = ResolveSpeakerName(line?.character);

        Plugin.Log.LogInfo($"[dialogue] {speaker}: \"{text}\"");

        if (!Plugin.Instance.CfgEnabled.Value || !Plugin.Instance.CfgDialogue.Value)
            return;

        TtsController.Instance?.Speak(speaker, text);
    }

    /// <summary>
    /// Map a dialogue character to the speaker name used for voice/prerender lookup.
    /// The player captain's Character.name is the user's chosen callsign/firstName,
    /// so we detect it by reference to <c>Characters.captain</c> and substitute one
    /// of the six captain preset names so prerender + voice mapping can find it.
    /// </summary>
    private static string ResolveSpeakerName(Character? character)
    {
        if (character == null) return "<unknown>";
        if (character == Characters.captain)
            return "captain_" + ResolveCaptainPreset();
        return character.name ?? "<unknown>";
    }

    private static string ResolveCaptainPreset()
    {
        var cfg = Plugin.Instance.CfgCaptainPreset.Value?.ToLowerInvariant() ?? "auto";
        if (cfg is "m1" or "m2" or "m3" or "f1" or "f2" or "f3") return cfg;

        // "auto" (or any invalid value) — pick by commander gender.
        var isFemale = GamePlayer.current?.commander?.gender == Gender.Female;
        return isFemale ? "f1" : "m1";
    }

    [HarmonyPrefix]
    [HarmonyPatch(nameof(DialogueManager.CloseDialogue))]
    private static void CloseDialogue_Prefix()
    {
        TtsController.Instance?.Stop();
    }
}
