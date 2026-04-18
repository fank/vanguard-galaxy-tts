#!/usr/bin/env python3
"""Extract dialogue lines that embed captain.name, as runtime-substitutable templates.

Output: prerender/captain_name_templates.json — shipped with the mod.

At runtime (Characters.CreateCaptain postfix), the plugin reads this list,
substitutes {captain} with the actual commander callsign, and warms the
DiskCache via live Kokoro synthesis. So when the line fires in dialogue,
playback is instant — no synth delay on the hot path.

Only lines that are "captain.name plus literals and <char>.name references"
are captured. Lines with Translation/POI/Faction-dynamic parts are skipped
and fall back to on-demand synthesis.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
# Reuse the v2 extractor's helpers
from extract_dialogue_v2 import (
    DECOMP, DIALOGUE_FILES, balance_parens, split_top_level_commas,
    build_character_name_map, unescape_cs,
)

OUT = Path(__file__).parent.parent.parent / "prerender" / "captain_name_templates.json"

CAPTAIN_PLACEHOLDER = "{captain}"


def evaluate_template(expr: str, name_map: dict[str, str]) -> str | None:
    """Like evaluate_text_expr but replaces captain.name with {captain}.
    Returns None if any non-literal / non-char-name / non-captain.name token appears."""
    expr = expr.strip()

    # Tokenize on + at depth 0
    tokens: list[str] = []
    depth = 0; in_str = False; escape = False
    buf = []
    for c in expr:
        if in_str:
            buf.append(c)
            if escape: escape = False
            elif c == "\\": escape = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True; buf.append(c)
            elif c == "(": depth += 1; buf.append(c)
            elif c == ")": depth -= 1; buf.append(c)
            elif c == "+" and depth == 0:
                tokens.append("".join(buf).strip()); buf = []
            else: buf.append(c)
    if buf: tokens.append("".join(buf).strip())

    parts: list[str] = []
    for t in tokens:
        lit = re.fullmatch(r'"((?:\\.|[^"\\])*)"', t)
        if lit:
            parts.append(unescape_cs(lit.group(1)))
            continue
        # captain.name OR Characters.captain.name
        if re.fullmatch(r'(?:Characters\.)?captain\.name', t):
            parts.append(CAPTAIN_PLACEHOLDER)
            continue
        # Other <char>.name — only if known
        m = re.fullmatch(r'(\w+)\.name', t)
        if m and m.group(1) in name_map:
            parts.append(name_map[m.group(1)])
            continue
        # Anything else (Translation.*, POI.*, Faction.*, etc.) — bail
        return None
    return "".join(parts)


def main():
    name_map = build_character_name_map()
    # Override conquest commanders whose factory uses Translation.Translate()
    # instead of a string literal. The build_character_name_map regex scanner
    # can't resolve them; these are mapped explicitly here.
    name_map.update({
        "canisecConquestCommander":  "Cade Callahan",
        "kolyatovConquestCommander": "Mikhail Kolyatov",
        "luminateConquestCommander": "Triane Solis",
        "stellarConquestCommander":  "Victor Hale",
    })
    templates: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for f in DIALOGUE_FILES:
        path = DECOMP / f
        if not path.exists(): continue
        src = path.read_text()
        for m in re.finditer(r'\bcDL\s*\(', src):
            open_paren = m.end() - 1
            close_paren = balance_parens(src, open_paren)
            if close_paren < 0: continue
            args = src[open_paren + 1:close_paren]
            parts = split_top_level_commas(args)
            if len(parts) < 2: continue
            speaker_expr = parts[0].strip()
            text_expr = parts[1].strip()
            if "captain.name" not in text_expr: continue
            template = evaluate_template(text_expr, name_map)
            if template is None or CAPTAIN_PLACEHOLDER not in template:
                continue

            # Resolve speaker via the character name map (matches resolve_speakers.py logic)
            sp = None
            m_chars = re.fullmatch(r'Characters\.(\w+)', speaker_expr)
            if m_chars and m_chars.group(1) in name_map:
                sp = name_map[m_chars.group(1)]
            elif speaker_expr in name_map:
                sp = name_map[speaker_expr]

            if not sp: continue
            key = (sp, template)
            if key in seen: continue
            seen.add(key)
            templates.append({"speaker": sp, "template": template})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(templates, indent=2, ensure_ascii=False))
    print(f"Captured {len(templates)} captain.name templates → {OUT}")
    for t in templates[:5]:
        print(f"  {t['speaker']:20s}  {t['template'][:70]!r}")


if __name__ == "__main__":
    main()
