using Behaviour.UI.HUD;
using HarmonyLib;
using VGTTS.Audio;

namespace VGTTS.Patches;

/// <summary>
/// Patches on <see cref="EchoRemarks"/>:
///   • Postfix on <c>SetMessage</c> — receives already-translated text (what the player
///     actually sees), so no localization-key handling needed.
///   • Prefix on <c>HideMessage</c> — cut the voice when the tip fades out (timer
///     expiry or click-to-dismiss).
///   • Prefix on <c>OnDisable</c> — cut the voice when the HUD widget is disabled
///     (e.g. opening the galaxy map).
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

        if (!EchoTipFilter.ShouldSpeak(text))
            return;

        TtsController.Instance?.Speak("ECHO", text);
    }

    [HarmonyPrefix]
    [HarmonyPatch(nameof(EchoRemarks.HideMessage))]
    private static void HideMessage_Prefix()
    {
        TtsController.Instance?.Stop();
    }

    [HarmonyPrefix]
    [HarmonyPatch("OnDisable")]
    private static void OnDisable_Prefix()
    {
        TtsController.Instance?.Stop();
    }
}
