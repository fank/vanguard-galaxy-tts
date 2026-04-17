using System.Text.RegularExpressions;

namespace VGTTS.Text;

/// <summary>
/// Preprocesses dialogue text so TTS engines (particularly Piper) produce natural
/// pauses where punctuation suggests them. Piper's espeak-based phonemizer tends
/// to elide runs of dots entirely — "We were... I guess... just one" comes out as
/// "We were I guess just one" with no break. We fix this by substituting:
///   • trailing ".." or more → "."        (softer full stop)
///   • ".." or more before uppercase word → ". " (sentence break)
///   • ".." or more before lowercase or lone "I" → ", "  (mid-sentence comma pause)
/// Threshold is 2+ dots so common typos like "well.. uh" get handled too. Unicode
/// U+2026 "…" is folded to ASCII first.
/// </summary>
internal static class TextNormalizer
{
    // Ellipsis at end of string. Consumes any trailing whitespace.
    private static readonly Regex TrailingEllipsis =
        new(@"(?:\.\s*){2,}\s*$", RegexOptions.Compiled);

    // "..." (possibly dot-space-dot) before a capital letter that is NOT a lone
    // first-person "I". Treated as a sentence break.
    //   (?!I\b) — negative lookahead: "I" followed by a word boundary is excluded
    //             so "I guess" doesn't trigger a period mid-sentence.
    private static readonly Regex SentenceBreakEllipsis =
        new(@"(?:\.\s*){2,}(?=\s*(?!I\b)[A-Z])", RegexOptions.Compiled);

    // Any remaining "..." — treated as a comma-sized pause.
    private static readonly Regex MidSentenceEllipsis =
        new(@"(?:\.\s*){2,}", RegexOptions.Compiled);

    // Collapse runs of whitespace introduced by substitutions.
    private static readonly Regex MultiSpace = new(@"\s{2,}", RegexOptions.Compiled);

    public static string ForTts(string text)
    {
        if (string.IsNullOrEmpty(text)) return text;

        // Fold Unicode ellipsis to ASCII so a single rule set covers both forms.
        text = text.Replace("\u2026", "...");

        text = TrailingEllipsis.Replace(text, ".");
        text = SentenceBreakEllipsis.Replace(text, ". ");
        text = MidSentenceEllipsis.Replace(text, ", ");

        text = MultiSpace.Replace(text, " ").Trim();
        return text;
    }
}
