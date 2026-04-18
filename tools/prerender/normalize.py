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
    # Smoke test
    import json
    tips = json.load(open("tools/prerender/echo_tips.json"))
    print(f"Loaded {len(tips)} ECHO tips")
    for i, (key, text) in enumerate(list(tips.items())[:5]):
        norm = for_tts(text)
        print(f"\n{key}:")
        print(f"  raw:  {text!r}")
        print(f"  norm: {norm!r}")
        print(f"  key:  {prerender_key(text, 'ECHO')}")
