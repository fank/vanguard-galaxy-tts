using System.Linq;
using BepInEx;
using BepInEx.Configuration;
using BepInEx.Logging;
using HarmonyLib;
using VGTTS.Audio;
using VGTTS.Cache;
using VGTTS.Prerender;
using VGTTS.TTS;
using VGTTS.Voice;

namespace VGTTS;

[BepInPlugin(PluginGuid, PluginName, PluginVersion)]
[BepInProcess("VanguardGalaxy.exe")]
public class Plugin : BaseUnityPlugin
{
    public const string PluginGuid = "dev.fankserver.vgtts";
    public const string PluginName = "Vanguard Galaxy TTS";
    // BepInEx parses PluginVersion through System.Version which rejects SemVer
    // pre-release suffixes, so stick to the plain N.N.N form.
    public const string PluginVersion = "1.1.0";

    internal static Plugin Instance { get; private set; } = null!;
    internal static ManualLogSource Log { get; private set; } = null!;

    internal ConfigEntry<bool> CfgEnabled = null!;
    internal ConfigEntry<bool> CfgDialogue = null!;
    internal ConfigEntry<bool> CfgEcho = null!;
    internal ConfigEntry<string> CfgProvider = null!;
    internal ConfigEntry<string> CfgPiperDefaultVoice = null!;
    internal ConfigEntry<int> CfgKokoroDefaultSpeaker = null!;
    internal ConfigEntry<string> CfgCaptainPreset = null!;

    private Harmony _harmony = null!;

    private void Awake()
    {
        Instance = this;
        Log = Logger;

        CfgEnabled           = Config.Bind("General", "Enabled",           true,  "Master enable/disable for TTS.");
        CfgDialogue          = Config.Bind("General", "DialogueTTS",       true,  "Speak NPC dialogue lines.");
        CfgEcho              = Config.Bind("General", "EchoTTS",           true,  "Speak ECHO ambient HUD tips.");
        CfgProvider          = Config.Bind("General", "Provider",          "piper", "TTS backend: sapi | piper");
        CfgPiperDefaultVoice = Config.Bind("Piper",   "DefaultVoice",      "en_US-hfc_female-medium",
            "Default Piper voice ID (filename without .onnx extension), used when a " +
            "character has no per-speaker entry under [Voices]. Bundled voices: " +
            "en_US-amy-medium, en_US-hfc_female-medium, en_US-kristin-medium, " +
            "en_US-ryan-medium, en_US-ryan-high, en_US-lessac-high, " +
            "en_GB-alan-medium, en_GB-jenny_dioco-medium.");
        CfgKokoroDefaultSpeaker = Config.Bind("Kokoro", "DefaultSpeaker", 0,
            "Default Kokoro speaker ID (0-102 in v1.1) when a Voices entry is " +
            "'kokoro:' with no number. Voices prefixed 'kokoro:' use Kokoro " +
            "regardless of the [General] Provider setting — set 'Voices.ECHO = kokoro:23' " +
            "to route only that character to Kokoro.");
        CfgCaptainPreset = Config.Bind("Voice", "CaptainPreset", "auto",
            "Voice preset for the player captain. 'auto' picks m1 or f1 based on " +
            "commander gender. Options: auto, m1 (am_fenrir rugged American), " +
            "m2 (am_onyx deep), m3 (bm_fable British rogue), f1 (af_alloy calm), " +
            "f2 (bf_alice British), f3 (af_heart warm flagship).");

        ITtsProvider primary = CreateProvider();
        ITtsProvider? kokoro = TryCreateKokoroProvider();
        ITtsProvider router = new ProviderRouter(primary, kokoro);

        var voiceMapper = new VoiceMapper(Config, CfgPiperDefaultVoice.Value, DefaultVoiceMap.Seeds);
        var prerender = new PrerenderLookup();
        var unprerendered = new UnprerenderedLog();
        TtsController.Instance = new TtsController(router, new DiskCache(), voiceMapper, prerender, unprerendered);
        Log.LogInfo($"TTS provider: {router.Name}, NPC profiles seeded: {DefaultVoiceMap.Seeds.Count}, " +
                    $"prerender entries: {prerender.EntryCount}, " +
                    $"prior prerender-misses: {unprerendered.SeenCount}");

        _harmony = new Harmony(PluginGuid);
        _harmony.PatchAll(typeof(Patches.DialogueManagerPatches));
        _harmony.PatchAll(typeof(Patches.EchoRemarksPatches));
        _harmony.PatchAll(typeof(Patches.CharactersPatches));
        Log.LogInfo($"{PluginName} v{PluginVersion} loaded ({_harmony.GetPatchedMethods().Count()} patches)");
    }

    private ITtsProvider CreateProvider()
    {
        switch (CfgProvider.Value?.ToLowerInvariant())
        {
            case "piper":
                try
                {
                    return new PiperProvider(CfgPiperDefaultVoice.Value);
                }
                catch (System.IO.FileNotFoundException ex)
                {
                    Log.LogWarning($"Piper bundle not found, falling back to SAPI. ({ex.Message})");
                    return new SapiProvider();
                }
            case "sapi":
            default:
                return new SapiProvider();
        }
    }

    private ITtsProvider? TryCreateKokoroProvider()
    {
        try
        {
            return new KokoroProvider(CfgKokoroDefaultSpeaker.Value);
        }
        catch (System.IO.FileNotFoundException)
        {
            // Kokoro bundle is optional — any `kokoro:` voice entry just falls
            // through to the primary provider in its absence.
            return null;
        }
    }

    private void OnDestroy()
    {
        _harmony?.UnpatchSelf();
    }
}
