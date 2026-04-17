using System.Collections.Generic;

namespace VGTTS.Voice;

/// <summary>
/// Per-NPC voice profiles — all on Kokoro v1.0 for its markedly better <c>?</c>
/// and <c>!</c> intonation compared to Piper. Each NPC gets a unique
/// <c>(speaker, pitch)</c> combination so no two characters sound alike.
///
/// Kokoro v1.0 multi-lang offers 15 English-female (ids 0-10, 20-23) and
/// 13 English-male (ids 11-19, 24-27) speakers. Since we have 26 male NPCs
/// against 13 male speakers, male roles reuse speaker IDs with pitch offsets
/// (0.94 / 1.00 / 1.06) — subtle enough to stay natural, distinct enough that
/// two NPCs on <c>am_michael</c> don't sound identical.
///
/// User overrides: edit <c>[Voices]</c> and <c>[Pitch]</c> in the config.
/// Prefix <c>kokoro:</c> routes to Kokoro; any other value (e.g. an <c>.onnx</c>
/// filename) routes back to Piper.
/// </summary>
internal static class DefaultVoiceMap
{
    public static IReadOnlyDictionary<string, (string Voice, float Pitch)> Seeds { get; } =
        new Dictionary<string, (string, float)>
        {
            // Spotlight — hand-pinned
            ["ECHO"]              = ("kokoro:21", 1.00f),  // bf_emma  — British female, validated

            // Starter zone
            ["Greg"]              = ("kokoro:25", 1.00f),  // bm_fable
            ["Elena"]             = ("kokoro:3",  1.00f),  // af_heart
            ["Creed"]             = ("kokoro:24", 1.00f),  // bm_daniel
            ["Virgil"]            = ("kokoro:25", 0.94f),  // bm_fable, deeper

            // Umbral / Darkspace antagonists
            ["Unknown Contact"]   = ("kokoro:11", 1.00f),  // am_adam
            ["Umbral"]            = ("kokoro:13", 0.94f),  // am_eric, deeper
            ["Midas"]             = ("kokoro:25", 1.06f),  // bm_fable, higher

            // Story NPCs
            ["Arle"]              = ("kokoro:11", 1.06f),  // am_adam, higher
            ["Prison Guard"]      = ("kokoro:16", 1.06f),  // am_michael, higher
            ["John Raythor"]      = ("kokoro:17", 1.06f),  // am_onyx, higher
            ["Keril"]             = ("kokoro:26", 1.00f),  // bm_george
            ["Thundo Klipz"]      = ("kokoro:13", 1.06f),  // am_eric, higher
            ["Adeline Lorentz"]   = ("kokoro:1",  1.00f),  // af_aoede
            ["Mick Flank"]        = ("kokoro:16", 0.94f),  // am_michael, deeper
            ["James Fleddon"]     = ("kokoro:24", 0.94f),  // bm_daniel, deeper
            ["Claude"]            = ("kokoro:24", 1.06f),  // bm_daniel, higher
            ["Stella Chion"]      = ("kokoro:6",  1.00f),  // af_nicole
            ["Melloy"]            = ("kokoro:27", 1.00f),  // bm_lewis

            // Skilltree instructors
            ["Elias McIntire"]    = ("kokoro:15", 0.94f),  // am_liam, deeper
            ["Olga Skarsgard"]    = ("kokoro:7",  1.00f),  // af_nova
            ["Alice Okono"]       = ("kokoro:4",  1.00f),  // af_jessica
            ["Brandon Wallace"]   = ("kokoro:17", 1.00f),  // am_onyx
            ["Oron"]              = ("kokoro:14", 1.00f),  // am_fenrir
            ["Sergeant Ogolin"]   = ("kokoro:14", 0.94f),  // am_fenrir, deeper
            ["Margot Cash"]       = ("kokoro:8",  1.00f),  // af_river

            // Mission givers
            ["Etienne Briggs"]    = ("kokoro:14", 1.06f),  // am_fenrir, higher
            ["Amalia Rodriguez"]  = ("kokoro:9",  1.00f),  // af_sarah
            ["Gabriel Ramos"]     = ("kokoro:15", 1.06f),  // am_liam, higher
            ["Edar Thopter"]      = ("kokoro:18", 1.00f),  // am_puck
            ["Sergio Weisartz"]   = ("kokoro:26", 0.94f),  // bm_george, deeper
            ["Brenda Diamond"]    = ("kokoro:23", 1.00f),  // bf_lily
            ["Anton Havel"]       = ("kokoro:18", 0.94f),  // am_puck, deeper

            // Conquest gateways
            ["Waldo Everson"]     = ("kokoro:17", 0.94f),  // am_onyx, deeper
            ["Lynn Bree"]         = ("kokoro:2",  1.00f),  // af_bella
            ["Horace the Red"]    = ("kokoro:19", 0.94f),  // am_santa, deeper
            ["Mirthe Coman"]      = ("kokoro:0",  1.00f),  // af_alloy
        };
}
