using System.Collections.Generic;

namespace VGTTS.Voice;

/// <summary>
/// Per-NPC voice profiles — (voice, pitch) tuples. Five spotlight characters (ECHO,
/// Greg, Elena, Creed, Virgil) keep premium single-speaker models tuned by pitch.
/// The remaining 32 NPCs use distinct speakers from <c>en_US-libritts_r-medium</c>'s
/// 904-speaker multi-speaker model; speaker IDs were hash-picked from the 888 that
/// have high-confidence gender annotations in LibriTTS-P, guaranteeing a unique,
/// gender-correct voice per NPC. Trait tags (from LibriTTS-P) are inline as comments
/// so you can see what each speaker sounds like before launching the game.
///
/// Users override any entry via the <c>[Voices]</c> / <c>[Pitch]</c> config sections.
/// </summary>
internal static class DefaultVoiceMap
{
    private const string LR = "en_US-libritts_r-medium";

    public static IReadOnlyDictionary<string, (string Voice, float Pitch)> Seeds { get; } =
        new Dictionary<string, (string, float)>
        {
            // Spotlight — premium single-speaker models
            ["ECHO"]              = ("en_GB-jenny_dioco-medium", 1.00f),
            ["Greg"]              = ("en_US-ryan-high",          0.97f),
            ["Elena"]             = ("en_US-hfc_female-medium",  1.03f),
            ["Creed"]             = ("en_US-lessac-high",        0.95f),
            ["Virgil"]            = ("en_GB-alan-medium",        1.02f),

            // Umbral / Darkspace antagonists
            ["Unknown Contact"]   = ($"{LR}/642", 1.00f),  // masculine, middle-aged, tensed
            ["Umbral"]            = ($"{LR}/393", 1.00f),  // masculine, adult-like, tensed
            ["Midas"]             = ($"{LR}/254", 1.00f),  // masculine, adult-like, tensed

            // Story NPCs
            ["Arle"]              = ($"{LR}/889", 1.00f),  // masculine, adult-like, bright
            ["Prison Guard"]      = ($"{LR}/643", 1.00f),  // masculine, adult-like, slightly thin
            ["John Raythor"]      = ($"{LR}/189", 1.00f),  // masculine, middle-aged, tensed
            ["Keril"]             = ($"{LR}/607", 1.00f),  // masculine, adult-like, thick
            ["Thundo Klipz"]      = ($"{LR}/605", 1.00f),  // masculine, adult-like, tensed
            ["Adeline Lorentz"]   = ($"{LR}/157", 1.00f),  // feminine, adult-like
            ["Mick Flank"]        = ($"{LR}/839", 1.00f),  // masculine, adult-like, relaxed
            ["James Fleddon"]     = ($"{LR}/499", 1.00f),  // masculine, middle-aged, thick
            ["Claude"]            = ($"{LR}/486", 1.00f),  // masculine, middle-aged, tensed
            ["Stella Chion"]      = ($"{LR}/790", 1.00f),  // feminine, adult-like
            ["Melloy"]            = ($"{LR}/805", 1.00f),  // masculine, middle-aged, thick

            // Skilltree instructors
            ["Elias McIntire"]    = ($"{LR}/818", 1.00f),  // masculine, adult-like, tensed
            ["Olga Skarsgard"]    = ($"{LR}/764", 1.00f),  // feminine, adult-like, tensed
            ["Alice Okono"]       = ($"{LR}/12",  1.00f),  // feminine, adult-like, tensed
            ["Brandon Wallace"]   = ($"{LR}/697", 1.00f),  // masculine, adult-like, slightly thin
            ["Oron"]              = ($"{LR}/519", 1.00f),  // masculine, slightly old, thick
            ["Sergeant Ogolin"]   = ($"{LR}/804", 1.00f),  // masculine, adult-like
            ["Margot Cash"]       = ($"{LR}/626", 1.00f),  // feminine, adult-like, bright

            // Mission givers
            ["Etienne Briggs"]    = ($"{LR}/270", 1.00f),  // masculine, middle-aged, tensed
            ["Amalia Rodriguez"]  = ($"{LR}/702", 1.00f),  // feminine, young, tensed
            ["Gabriel Ramos"]     = ($"{LR}/760", 1.00f),  // masculine, adult-like, tensed
            ["Edar Thopter"]      = ($"{LR}/767", 1.00f),  // masculine, middle-aged, tensed
            ["Sergio Weisartz"]   = ($"{LR}/879", 1.00f),  // masculine, adult-like
            ["Brenda Diamond"]    = ($"{LR}/692", 1.00f),  // feminine, adult-like, relaxed
            ["Anton Havel"]       = ($"{LR}/867", 1.00f),  // masculine, middle-aged, thick

            // Conquest gateways
            ["Waldo Everson"]     = ($"{LR}/8",   1.00f),  // masculine, adult-like, tensed
            ["Lynn Bree"]         = ($"{LR}/107", 1.00f),  // feminine, adult-like, tensed
            ["Horace the Red"]    = ($"{LR}/690", 1.00f),  // masculine, adult-like, bright
            ["Mirthe Coman"]      = ($"{LR}/101", 1.00f),  // feminine, adult-like, relaxed
        };
}
