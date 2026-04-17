using System.Collections.Generic;

namespace VGTTS.Voice;

/// <summary>
/// Gender/role-guessed default voice assignments for every named NPC in the game,
/// extracted from <c>Source.Dialogues.Characters</c>. Users override via config.
/// Conquest faction commanders use localized names (Translation.Translate) so they
/// cannot be pre-seeded; they auto-bind to <c>default</c> on first encounter.
/// </summary>
internal static class DefaultVoiceMap
{
    // Medium tier — mass NPCs
    private const string Amy     = "en_US-amy-medium";            // female, US
    private const string Kristin = "en_US-kristin-medium";        // female, US, smoother than Amy
    private const string Hfc     = "en_US-hfc_female-medium";     // female, US, studio-quality corpus
    private const string Ryan    = "en_US-ryan-medium";           // male, US
    private const string Alan    = "en_GB-alan-medium";           // male, UK — antagonist / authority

    // High tier — reserved for spotlight characters (ECHO, captain, named story NPCs)
    private const string Jenny   = "en_GB-jenny_dioco-medium";    // female, UK, studio dataset — AI feel
    private const string Lessac  = "en_US-lessac-high";           // male, US, highest Piper quality
    private const string RyanHi  = "en_US-ryan-high";             // male, US, higher quality

    public static IReadOnlyDictionary<string, string> Seeds { get; } = new Dictionary<string, string>
    {
        // Ship AI — studio-quality British female, distinct AI feel
        ["ECHO"]              = Jenny,

        // Starter zone — upgraded to high-tier voices (these are heard a lot)
        ["Greg"]              = RyanHi,
        ["Elena"]             = Hfc,
        ["Creed"]             = Lessac,
        ["Virgil"]            = Alan,

        // Umbral Reach
        ["Unknown Contact"]   = Alan,
        ["Umbral"]            = Alan,
        ["Midas"]             = Alan,

        // Story NPCs
        ["Arle"]              = Alan,
        ["Prison Guard"]      = Ryan,
        ["John Raythor"]      = Ryan,
        ["Keril"]             = Ryan,
        ["Thundo Klipz"]      = Ryan,
        ["Adeline Lorentz"]   = Amy,
        ["Mick Flank"]        = Ryan,
        ["James Fleddon"]     = Ryan,
        ["Claude"]            = Ryan,
        ["Stella Chion"]      = Amy,
        ["Melloy"]            = Ryan,

        // Skilltree instructors — vary voices so back-to-back tutorials don't homogenize
        ["Elias McIntire"]    = Ryan,
        ["Olga Skarsgard"]    = Hfc,
        ["Alice Okono"]       = Kristin,
        ["Brandon Wallace"]   = Lessac,
        ["Oron"]              = Alan,
        ["Sergeant Ogolin"]   = Ryan,
        ["Margot Cash"]       = Kristin,

        // Mission givers
        ["Etienne Briggs"]    = Alan,
        ["Amalia Rodriguez"]  = Hfc,
        ["Gabriel Ramos"]     = Ryan,
        ["Edar Thopter"]      = Ryan,
        ["Sergio Weisartz"]   = Ryan,
        ["Brenda Diamond"]    = Kristin,
        ["Anton Havel"]       = Ryan,

        // Conquest gateways
        ["Waldo Everson"]     = Ryan,
        ["Lynn Bree"]         = Hfc,
        ["Horace the Red"]    = Alan,
        ["Mirthe Coman"]      = Kristin,
    };
}
