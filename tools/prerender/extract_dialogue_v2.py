#!/usr/bin/env python3
"""Dialogue extractor v2 — handles string-concatenation patterns.

The original extractor (now deleted) captured only pure string literals:
    DialogueLine.cDL(speaker, "literal text")

But the game has many lines that build text at runtime via concatenation:
    DialogueLine.cDL(elena, "I'd like to stay with " + creed.name + ".")

These slipped through. This extractor parses the full argument expression
for each cDL call (balanced-paren), then evaluates concat chains, resolving
<char>.name references to the character's known name.

Skipped (can't resolve at build time):
  - captain.name / captain.firstName — player's chosen name
  - Anything else non-literal and non-character-name

Output: /tmp/dialogue_lines_v2.json — list of {speaker, text, file, line}.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

DECOMP = Path("/tmp/decomp")
OUT = Path("/tmp/dialogue_lines_v2.json")

DIALOGUE_FILES = [
    "Behaviour.Dialogues/DialogueManager.cs",
    "Source.Dialogues/DialogueLine.cs",
    "Source.Dialogues.Content/SkilltreeMissions.cs",
    "Source.Dialogues.Content/SideMissions.cs",
    "Source.Dialogues.Content/ConquestMissions.cs",
    "Source.Simulation.World.POI/DistressCombat.cs",
    "Source.Galaxy.POI.Station.Patrons/Salesman.cs",
    "Source.Galaxy.POI.Station.Patrons/CrewMember.cs",
    "Source.Simulation.Story/Puppeteers.cs",
    "Source.Simulation.Story/Tutorial.cs",
]


def build_character_name_map() -> dict[str, str]:
    """Parse Characters.cs factory methods, build field/property → display-name map.

    Handles:
      public static Character greg => _greg ?? (_greg = Greg());  // prop → factory
      public static Character Greg() { ... CreateCharacter("Greg") ... }  // factory → name
    """
    src = (DECOMP / "Source.Dialogues/Characters.cs").read_text()
    # Property → factory name
    prop_to_factory: dict[str, str] = {}
    for m in re.finditer(
        r'public\s+static\s+Character\s+(\w+)\s*=>\s*\w+\s*\?\?\s*\(\w+\s*=\s*(\w+)\(\)\)',
        src,
    ):
        prop_to_factory[m.group(1)] = m.group(2)

    # Factory name → CreateCharacter("<name>")
    factory_to_name: dict[str, str] = {}
    for m in re.finditer(
        r'public\s+static\s+Character\s+(\w+)\s*\([^)]*\)\s*\{.*?CreateCharacter\s*\(\s*"([^"]+)"',
        src, re.DOTALL,
    ):
        factory_to_name[m.group(1)] = m.group(2)

    # Property → name
    result: dict[str, str] = {}
    for prop, factory in prop_to_factory.items():
        if factory in factory_to_name:
            result[prop] = factory_to_name[factory]

    # Manual additions — non-property characters
    # `shipAi` field is assigned separately in CreateShipAi, and we've pinned it as ECHO.
    result["shipAi"] = "ECHO"
    return result


def balance_parens(src: str, start: int) -> int:
    """Given src[start] points to '(', return index of matching ')'."""
    depth = 0
    in_str = False
    escape = False
    i = start
    while i < len(src):
        c = src[i]
        if in_str:
            if escape: escape = False
            elif c == "\\": escape = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True
            elif c == "(": depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0: return i
        i += 1
    return -1


def split_top_level_commas(args: str) -> list[str]:
    """Split 'a, b(c,d), e' → ['a', 'b(c,d)', 'e']."""
    parts: list[str] = []
    depth = 0
    in_str = False
    escape = False
    buf = []
    for c in args:
        if in_str:
            buf.append(c)
            if escape: escape = False
            elif c == "\\": escape = True
            elif c == '"': in_str = False
        else:
            if c == '"': in_str = True; buf.append(c)
            elif c == "(": depth += 1; buf.append(c)
            elif c == ")": depth -= 1; buf.append(c)
            elif c == "," and depth == 0:
                parts.append("".join(buf).strip())
                buf = []
            else: buf.append(c)
    if buf: parts.append("".join(buf).strip())
    return parts


def evaluate_text_expr(expr: str, name_map: dict[str, str]) -> str | None:
    """Evaluate a C# expression that's a chain of string literals and simple
    <char>.name references joined by '+'. Return the concatenated string, or
    None if any part can't be resolved."""
    expr = expr.strip()
    # Quick path: pure literal
    m = re.fullmatch(r'"((?:\\.|[^"\\])*)"', expr)
    if m:
        return unescape_cs(m.group(1))

    # Chain of '+' — tokenize.
    tokens: list[str] = []
    depth = 0
    in_str = False
    escape = False
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
                tokens.append("".join(buf).strip())
                buf = []
            else: buf.append(c)
    if buf: tokens.append("".join(buf).strip())

    parts: list[str] = []
    for t in tokens:
        lit = re.fullmatch(r'"((?:\\.|[^"\\])*)"', t)
        if lit:
            parts.append(unescape_cs(lit.group(1)))
            continue
        nm = re.fullmatch(r'(\w+)\.name', t)
        if nm and nm.group(1) in name_map:
            parts.append(name_map[nm.group(1)])
            continue
        # Unresolvable token — bail.
        return None
    return "".join(parts)


def unescape_cs(s: str) -> str:
    return s.replace('\\"', '"').replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t").replace("\\\\", "\\")


def extract_file(path: Path, name_map: dict[str, str]) -> list[dict]:
    src = path.read_text()
    rel = str(path.relative_to(DECOMP))
    results: list[dict] = []
    # cDL( can be DialogueLine.cDL(, .cDL(, or plain cDL(
    for m in re.finditer(r'\bcDL\s*\(', src):
        open_paren = m.end() - 1
        close_paren = balance_parens(src, open_paren)
        if close_paren < 0: continue
        args = src[open_paren + 1:close_paren]
        parts = split_top_level_commas(args)
        if len(parts) < 2: continue
        speaker_expr = parts[0].strip()
        text_expr = parts[1].strip()
        text = evaluate_text_expr(text_expr, name_map)
        if text is None or not text.strip(): continue
        # Count line
        line = src[:m.start()].count("\n") + 1
        results.append({
            "file": rel,
            "speaker": speaker_expr,
            "text": text,
            "line": line,
        })
    return results


def main():
    name_map = build_character_name_map()
    print(f"Character name map: {len(name_map)} entries")
    print(f"  sample: elena={name_map.get('elena')}, creed={name_map.get('creed')}, greg={name_map.get('greg')}")

    all_lines: list[dict] = []
    for f in DIALOGUE_FILES:
        path = DECOMP / f
        if not path.exists():
            print(f"  SKIP (not found): {f}")
            continue
        lines = extract_file(path, name_map)
        print(f"  {f}: {len(lines)}")
        all_lines.extend(lines)

    OUT.write_text(json.dumps(all_lines, indent=2, ensure_ascii=False))
    print(f"\nTotal: {len(all_lines)} lines → {OUT}")


if __name__ == "__main__":
    main()
