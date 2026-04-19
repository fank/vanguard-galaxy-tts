"""Text normalization for TTS rendering. Python mirror of VGTTS/Text/TextNormalizer.cs.

Both Python (render-time) and C# (runtime) must produce byte-identical output for
the pre-render cache lookup to work. If you change this file, update the C# file
and run the parity test.
"""
from __future__ import annotations
import re

_trailing_ellipsis = re.compile(r"(?:\.\s*){2,}\s*$")
_sentence_break_ellipsis = re.compile(r"(?:\.\s*){2,}(?=\s*(?!I\b)[A-Z])")
_mid_sentence_ellipsis = re.compile(r"(?:\.\s*){2,}")
_multi_space = re.compile(r"\s{2,}")


def for_tts(text: str) -> str:
    """Return the text as the TTS engine will see it.

    Mirrors the C# TextNormalizer.ForTts rules:
    - Unicode ellipsis U+2026 folded to ASCII "..."
    - Trailing "..." → "."
    - "..." before capital letter (not lone "I") → ". "
    - Remaining "..." → ", "
    - Collapse runs of whitespace, trim
    """
    if not text:
        return text
    text = text.replace("\u2026", "...")
    text = _trailing_ellipsis.sub(".", text)
    text = _sentence_break_ellipsis.sub(". ", text)
    text = _mid_sentence_ellipsis.sub(", ", text)
    text = _multi_space.sub(" ", text).strip()
    return text


def prerender_key(text: str, speaker: str) -> str:
    """Compute the cache-manifest key. MUST match the C# side exactly.

    Key format: sha256(normalize(text) + "\x00" + speaker_name) hex.
    """
    import hashlib
    normalized = for_tts(text)
    blob = normalized.encode("utf-8") + b"\x00" + speaker.encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


if __name__ == "__main__":
    # Parity dump — runs normalization over every ECHO tip and prints
    # (tip_id, raw, normalized, key) as TSV so a C# harness can diff and
    # catch any regressions in the Python ↔ C# normalizer pair.
    # A mismatch at runtime = cache miss = prerender doesn't kick in.
    import json
    from pathlib import Path
    tips = json.load(open(Path(__file__).parent / "echo_tips.json"))
    print("tip_id\traw\tnormalized\tkey")
    for k, v in sorted(tips.items()):
        v = v.strip()
        print(f"{k}\t{v!r}\t{for_tts(v)!r}\t{prerender_key(v, 'ECHO')}")
