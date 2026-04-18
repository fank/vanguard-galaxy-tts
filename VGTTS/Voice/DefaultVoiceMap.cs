using System.Collections.Generic;

namespace VGTTS.Voice;

/// <summary>
/// Per-NPC voice profiles — all on Kokoro v1.0 for its markedly better <c>?</c>
/// and <c>!</c> intonation compared to Piper. Each NPC gets a <c>(voice, pitch)</c>
/// combination.
///
/// Most NPCs have their prerender audio baked at a specific Kokoro SID via
/// Kokoro-direct synthesis. These entries intentionally use <b>pitch 1.00</b>
/// and the same SID so that runtime live-TTS produces byte-identical output
/// for any line that missed the prerender pack (commander-name substitutions,
/// post-patch additions, etc.) — same ONNX model, same SID, same text →
/// deterministic.
///
/// For NPCs whose prerender uses F5-TTS voice cloning on a <i>non-English</i>
/// Kokoro reference to get accent variety (Japanese/Hindi/Spanish/French/
/// Portuguese/Scottish), runtime live-TTS can't run F5 and falls back to the
/// SID below. This intentionally accepts a timbre mismatch between the
/// prerendered lines (accented) and the rare live-TTS lines (plain English)
/// for those NPCs — the mismatch affects only commander-name dialogue lines,
/// which are 0-3 per accented NPC.
///
/// User overrides: edit <c>[Voices]</c> and <c>[Pitch]</c> in the config.
/// Prefix <c>kokoro:</c> routes to Kokoro; any other value routes to Piper.
/// </summary>
internal static class DefaultVoiceMap
{
    public static IReadOnlyDictionary<string, (string Voice, float Pitch)> Seeds { get; } =
        new Dictionary<string, (string, float)>
        {
            // Spotlight
            ["ECHO"]              = ("kokoro:1",  1.00f),  // af_aoede — smooth & fatigue-resistant

            // Player captain — 6 presets, end-player picks via [Voice] CaptainPreset
            ["captain_m1"]        = ("kokoro:14", 1.00f),  // am_fenrir
            ["captain_m2"]        = ("kokoro:17", 1.00f),  // am_onyx
            ["captain_m3"]        = ("kokoro:25", 1.00f),  // bm_fable
            ["captain_f1"]        = ("kokoro:0",  1.00f),  // af_alloy
            ["captain_f2"]        = ("kokoro:20", 1.00f),  // bf_alice
            ["captain_f3"]        = ("kokoro:3",  1.00f),  // af_heart

            // Aligned with Kokoro-direct prerender — live-TTS matches byte-for-byte
            ["Greg"]              = ("kokoro:16", 1.00f),  // am_michael
            ["Elena"]             = ("kokoro:4",  1.00f),  // af_jessica
            ["Virgil"]            = ("kokoro:25", 1.00f),  // bm_fable
            ["Unknown Contact"]   = ("kokoro:25", 1.00f),  // bm_fable
            ["Umbral"]            = ("kokoro:25", 1.00f),  // bm_fable
            ["Midas"]             = ("kokoro:24", 1.00f),  // bm_daniel
            ["John Raythor"]      = ("kokoro:16", 1.00f),  // am_michael
            ["Keril"]             = ("kokoro:16", 1.00f),  // am_michael (placeholder — Russian accent gap)
            ["Thundo Klipz"]      = ("kokoro:13", 1.00f),  // am_eric
            ["Adeline Lorentz"]   = ("kokoro:21", 1.00f),  // bf_emma
            ["James Fleddon"]     = ("kokoro:17", 1.00f),  // am_onyx
            ["Brandon Wallace"]   = ("kokoro:13", 1.00f),  // am_eric
            ["Sergeant Ogolin"]   = ("kokoro:23", 1.00f),  // bf_lily
            ["Margot Cash"]       = ("kokoro:21", 1.00f),  // bf_emma
            ["Edar Thopter"]      = ("kokoro:22", 1.00f),  // bf_isabella
            ["Sergio Weisartz"]   = ("kokoro:18", 1.00f),  // am_puck (placeholder — German accent gap)
            ["Brenda Diamond"]    = ("kokoro:6",  1.00f),  // af_nicole
            ["Anton Havel"]       = ("kokoro:17", 1.00f),  // am_onyx
            ["Cade Callahan"]     = ("kokoro:16", 1.00f),  // am_michael
            ["Victor Hale"]       = ("kokoro:17", 1.00f),  // am_onyx
            ["Mikhail Kolyatov"]  = ("kokoro:17", 1.00f),  // am_onyx (placeholder — Russian accent gap)
            ["Waldo Everson"]     = ("kokoro:14", 1.00f),  // am_fenrir
            ["Lynn Bree"]         = ("kokoro:10", 1.00f),  // af_sky
            ["Horace the Red"]    = ("kokoro:24", 1.00f),  // bm_daniel
            ["Mirthe Coman"]      = ("kokoro:21", 1.00f),  // bf_emma
            ["Olga Skarsgard"]    = ("kokoro:23", 1.00f),  // bf_lily (placeholder — Nordic accent gap)
            ["Prison Guard"]      = ("kokoro:10", 1.00f),  // af_sky
            ["Melloy"]            = ("kokoro:18", 1.00f),  // am_puck

            // F5-cloned non-English prerender refs — live-TTS falls back to English
            // Kokoro SID for captain-name lines. Accepted mismatch for accent variety.
            ["Creed"]             = ("kokoro:33", 1.00f),  // hm_omega (F5 Hindi M in prerender)
            ["Arle"]              = ("kokoro:32", 1.00f),  // hf_beta (F5 Hindi F)
            ["Mick Flank"]        = ("kokoro:41", 1.00f),  // jm_kumo (F5 Japanese M)
            ["Stella Chion"]      = ("kokoro:40", 1.00f),  // jf_tebukuro (F5 Japanese F)
            ["Claude"]            = ("kokoro:30", 1.00f),  // ff_siwis (F5 French F)
            ["Alice Okono"]       = ("kokoro:31", 1.00f),  // hf_alpha (F5 Hindi F)
            ["Oron"]              = ("kokoro:43", 1.00f),  // pm_alex (F5 Portuguese M)
            ["Triane Solis"]      = ("kokoro:31", 1.00f),  // hf_alpha (F5 Hindi F)
            ["Etienne Briggs"]    = ("kokoro:30", 1.00f),  // ff_siwis (F5 French F)
            ["Amalia Rodriguez"]  = ("kokoro:28", 1.00f),  // ef_dora (F5 Spanish F)
            ["Gabriel Ramos"]     = ("kokoro:29", 1.00f),  // em_alex (F5 Spanish M)

            // Scottish via Piper (Kokoro has no Scottish speaker). Live falls back to an
            // English Kokoro equivalent for captain-name lines.
            ["Elias McIntire"]    = ("kokoro:15", 1.00f),  // am_liam (F5 Piper en_GB-alba in prerender)
        };
}
