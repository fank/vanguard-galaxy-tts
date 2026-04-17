using System.Collections.Generic;
using Behaviour.Dialogues;
using HarmonyLib;
using Source.Dialogues;
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
        var speaker = line?.character?.name ?? "<unknown>";
        var text = line?.text ?? string.Empty;

        Plugin.Log.LogInfo($"[dialogue] {speaker}: \"{text}\"");

        if (!Plugin.Instance.CfgEnabled.Value || !Plugin.Instance.CfgDialogue.Value)
            return;

        TtsController.Instance?.Speak(speaker, text);
    }

    [HarmonyPrefix]
    [HarmonyPatch(nameof(DialogueManager.CloseDialogue))]
    private static void CloseDialogue_Prefix()
    {
        TtsController.Instance?.Stop();
    }
}
