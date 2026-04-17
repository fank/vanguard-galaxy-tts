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

    // Runs of exclamation marks (e.g. "Wait!!") collapse to a single char; the
    // Exclamation/Question regexes then handle that single char.
    private static readonly Regex RepeatedExclaim = new(@"!{2,}", RegexOptions.Compiled);
    private static readonly Regex RepeatedQuestion = new(@"\?{2,}", RegexOptions.Compiled);

    // Mixed interrobang (?!, !?, ?!?! etc) → single "?" keeps question intonation.
    private static readonly Regex Interrobang = new(@"[!?]{2,}", RegexOptions.Compiled);

    // Collapse runs of whitespace introduced by substitutions.
    private static readonly Regex MultiSpace = new(@"\s{2,}", RegexOptions.Compiled);

    /// <summary>
    /// Normalize dialogue text for TTS synthesis.
    /// </summary>
    /// <param name="normalizeExclamation">If true, "!" is rewritten to "." (Piper's
    /// excitement intonation tends to sound clipped / unnatural).</param>
    /// <param name="normalizeQuestion">If true, "?" is rewritten to "." (Piper's
    /// question-rise intonation is inconsistent voice-to-voice).</param>
    public static string ForTts(string text, bool normalizeExclamation, bool normalizeQuestion)
    {
        if (string.IsNullOrEmpty(text)) return text;

        // Fold Unicode ellipsis to ASCII so a single rule set covers both forms.
        text = text.Replace("\u2026", "...");

        text = TrailingEllipsis.Replace(text, ".");
        text = SentenceBreakEllipsis.Replace(text, ". ");
        text = MidSentenceEllipsis.Replace(text, ", ");

        // Collapse runs + interrobangs *before* the optional punct-to-period rewrite,
        // so "Wait!!!" ends up as one glyph regardless of which flags are set.
        text = Interrobang.Replace(text, m => m.Value.Contains('?') ? "?" : "!");
        text = RepeatedExclaim.Replace(text, "!");
        text = RepeatedQuestion.Replace(text, "?");

        if (normalizeExclamation) text = text.Replace('!', '.');
        if (normalizeQuestion)    text = text.Replace('?', '.');

        text = MultiSpace.Replace(text, " ").Trim();
        return text;
    }
}
