using System.Collections.Generic;
using Behaviour.Dialogues;
using HarmonyLib;
using Source.Dialogues;
using VGTTS.Audio;

namespace VGTTS.Patches;

/// <summary>
/// Prefix on <see cref="DialogueManager"/>.ShowDialogueLine — fires once per line,
/// before the typewriter coroutine. <c>currentLineIndex</c> is set by callers, not
/// mutated inside the method, so reading the line here is stable.
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
}
