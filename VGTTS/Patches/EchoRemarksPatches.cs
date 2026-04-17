using Behaviour.UI.HUD;
using HarmonyLib;
using VGTTS.Audio;

namespace VGTTS.Patches;

/// <summary>
/// Postfix on <see cref="EchoRemarks"/>.SetMessage — receives already-translated text
/// (what the player actually sees), so no localization key handling needed.
/// </summary>
[HarmonyPatch(typeof(EchoRemarks))]
internal static class EchoRemarksPatches
{
    [HarmonyPostfix]
    [HarmonyPatch(nameof(EchoRemarks.SetMessage))]
    private static void SetMessage_Postfix(string text)
    {
        if (string.IsNullOrWhiteSpace(text)) return;

        Plugin.Log.LogInfo($"[echo] ECHO: \"{text}\"");

        if (!Plugin.Instance.CfgEnabled.Value || !Plugin.Instance.CfgEcho.Value)
            return;

        TtsController.Instance?.Speak("ECHO", text);
    }
}
