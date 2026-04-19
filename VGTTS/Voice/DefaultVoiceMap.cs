using System.Collections.Generic;

namespace VGTTS.Voice;

/// <summary>
/// Per-NPC voice seeds — Kokoro v1.0 SID per character. The prerender pack is
/// built with Kokoro-direct at the same SID listed here, so runtime live-TTS
/// (for lines that miss the manifest, e.g. commander-name substitutions or
/// post-patch additions) produces byte-identical audio — same ONNX model,
/// same SID, same text → deterministic.
///
/// Non-English Kokoro SIDs (30/ff_siwis, 31-33/hf/hm, 40-41/jf/jm, 28-29/ef/em,
/// 43/pm) give accent flavor on English text while remaining intelligible —
/// verified empirically before the full F5→Kokoro migration on 2026-04-19.
///
/// User overrides: edit <c>[Voices]</c> in the config. Prefix <c>kokoro:</c>
/// routes to Kokoro; any other value routes to Piper.
/// </summary>
internal static class DefaultVoiceMap
{
    public static IReadOnlyDictionary<string, string> Seeds { get; } =
        new Dictionary<string, string>
        {
            // Spotlight
            ["ECHO"]              = "kokoro:1",   // af_aoede — smooth & fatigue-resistant

            // Player captain — 6 presets, end-player picks via [Voice] CaptainPreset
            ["captain_m1"]        = "kokoro:14",  // am_fenrir
            ["captain_m2"]        = "kokoro:17",  // am_onyx
            ["captain_m3"]        = "kokoro:25",  // bm_fable
            ["captain_f1"]        = "kokoro:0",   // af_alloy
            ["captain_f2"]        = "kokoro:20",  // bf_alice
            ["captain_f3"]        = "kokoro:3",   // af_heart

            // English Kokoro speakers
            ["Greg"]              = "kokoro:16",  // am_michael
            ["Elena"]             = "kokoro:4",   // af_jessica
            ["Virgil"]            = "kokoro:25",  // bm_fable
            ["Unknown Contact"]   = "kokoro:25",  // bm_fable
            ["Umbral"]            = "kokoro:25",  // bm_fable
            ["Midas"]             = "kokoro:24",  // bm_daniel
            ["John Raythor"]      = "kokoro:16",  // am_michael
            ["Keril"]             = "kokoro:16",  // am_michael (placeholder — Russian accent gap)
            ["Thundo Klipz"]      = "kokoro:13",  // am_eric
            ["Adeline Lorentz"]   = "kokoro:21",  // bf_emma
            ["James Fleddon"]     = "kokoro:17",  // am_onyx
            ["Brandon Wallace"]   = "kokoro:13",  // am_eric
            ["Sergeant Ogolin"]   = "kokoro:23",  // bf_lily
            ["Margot Cash"]       = "kokoro:21",  // bf_emma
            ["Edar Thopter"]      = "kokoro:22",  // bf_isabella
            ["Sergio Weisartz"]   = "kokoro:18",  // am_puck (placeholder — German accent gap)
            ["Brenda Diamond"]    = "kokoro:6",   // af_nicole
            ["Anton Havel"]       = "kokoro:17",  // am_onyx
            ["Cade Callahan"]     = "kokoro:16",  // am_michael
            ["Victor Hale"]       = "kokoro:17",  // am_onyx
            ["Mikhail Kolyatov"]  = "kokoro:17",  // am_onyx (placeholder — Russian accent gap)
            ["Waldo Everson"]     = "kokoro:14",  // am_fenrir
            ["Lynn Bree"]         = "kokoro:10",  // af_sky
            ["Horace the Red"]    = "kokoro:24",  // bm_daniel
            ["Mirthe Coman"]      = "kokoro:21",  // bf_emma
            ["Olga Skarsgard"]    = "kokoro:23",  // bf_lily (placeholder — Nordic accent gap)
            ["Prison Guard"]      = "kokoro:10",  // af_sky
            ["Melloy"]            = "kokoro:18",  // am_puck

            // Non-English Kokoro SIDs — accent flavor on English text
            ["Creed"]             = "kokoro:33",  // hm_omega     (Hindi M, deep authoritative)
            ["Arle"]              = "kokoro:32",  // hf_beta      (Hindi F, commanding)
            ["Mick Flank"]        = "kokoro:41",  // jm_kumo      (Japanese M)
            ["Stella Chion"]      = "kokoro:40",  // jf_tebukuro  (Japanese F, soft)
            ["Claude"]            = "kokoro:30",  // ff_siwis     (French F)
            ["Alice Okono"]       = "kokoro:31",  // hf_alpha     (Hindi F, warm)
            ["Oron"]              = "kokoro:43",  // pm_alex      (Portuguese M)
            ["Triane Solis"]      = "kokoro:31",  // hf_alpha     (Hindi F, mystical)
            ["Etienne Briggs"]    = "kokoro:30",  // ff_siwis     (French F)
            ["Amalia Rodriguez"]  = "kokoro:28",  // ef_dora      (Spanish F)
            ["Gabriel Ramos"]     = "kokoro:29",  // em_alex      (Spanish M)

            // Scottish accent gap — Kokoro has no Scottish speaker; using American male
            ["Elias McIntire"]    = "kokoro:15",  // am_liam      (placeholder — need Scottish male)
        };
}
