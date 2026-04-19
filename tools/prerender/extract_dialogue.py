#!/usr/bin/env python3
"""Dialogue extractor v3 — resolves Translation.Translate() at build time.

v2 bailed on any token it couldn't statically evaluate, including
Translation.Translate(...). Many lines use translation keys for names that
don't vary per player:
    cDL(umbralContact, "... captured by the " + Translation.Translate(Faction.gold.name) + ".")
    cDL(umbralContact, "The location of the " + Translation.Translate("@UComputer") + ".")

Those resolve deterministically to "Luminate Combine" / "Command Cortex"
at runtime. This extractor loads the game's en-US TextAsset from Unity
resources via UnityPy, parses the ini-style key=value mapping, and pipes
those values into the expression evaluator so these lines extract cleanly.

Still skipped (truly unresolvable at build time):
  - captain.name / captain.firstName — per-player callsign
  - Translation.Translate with dynamic keys (rare; e.g. Faction rank keys)
  - POI names / mission-dynamic tokens (MapPointOfInterest.current.name)
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

DECOMP = Path("/tmp/decomp")
GAME_RESOURCES = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Vanguard Galaxy/VanguardGalaxy_Data/resources.assets")

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


def unescape_cs(s: str) -> str:
    return s.replace('\\"', '"').replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t").replace("\\\\", "\\")


def balance_parens(src: str, start: int) -> int:
    depth = 0; in_str = False; escape = False
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
    parts: list[str] = []
    depth = 0; in_str = False; escape = False
    buf: list[str] = []
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
                parts.append("".join(buf).strip()); buf = []
            else: buf.append(c)
    if buf: parts.append("".join(buf).strip())
    return parts


def build_character_name_map() -> dict[str, str]:
    """Parse Characters.cs for property → factory → CreateCharacter("name") chains.
    Extracts each factory's body via brace-matching to avoid cross-function bleed."""
    src = (DECOMP / "Source.Dialogues/Characters.cs").read_text()

    prop_to_factory: dict[str, str] = {}
    for m in re.finditer(
        r'public\s+static\s+Character\s+(\w+)\s*=>\s*\w+\s*\?\?\s*\(\w+\s*=\s*(\w+)\(\)\)',
        src,
    ):
        prop_to_factory[m.group(1)] = m.group(2)

    # Brace-match each factory body, then find CreateCharacter("literal") inside it.
    factory_to_name: dict[str, str] = {}
    i = 0
    while True:
        m = re.search(r'public\s+static\s+Character\s+(\w+)\s*\([^)]*\)\s*\{', src[i:])
        if not m: break
        func_name = m.group(1)
        start = i + m.end() - 1
        depth = 0; j = start
        while j < len(src):
            if src[j] == '{': depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0: break
            j += 1
        body = src[start+1:j]
        cc = re.search(r'CreateCharacter\s*\(\s*"([^"]+)"', body)
        if cc: factory_to_name[func_name] = cc.group(1)
        i = j + 1

    result: dict[str, str] = {}
    for prop, factory in prop_to_factory.items():
        if factory in factory_to_name:
            result[prop] = factory_to_name[factory]

    result["shipAi"] = "ECHO"
    return result
OUT = Path("/tmp/dialogue_lines_v3.json")


def load_translations() -> dict[str, str]:
    """Read en-US TextAsset from Unity's resources.assets bundle."""
    import UnityPy
    env = UnityPy.load(str(GAME_RESOURCES))
    for obj in env.objects:
        if obj.type.name != "TextAsset": continue
        data = obj.read()
        if getattr(data, "m_Name", "") != "en-US": continue
        text = data.m_Script
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        return parse_ini(text)
    raise RuntimeError("en-US TextAsset not found in resources.assets")


def parse_ini(text: str) -> dict[str, str]:
    """Parse the game's ini-style translation file. Mirrors Translation.cs regex
    (`^\\s*(.+?)\\s*=(.*)`) and its comment skip rule (`^\\s*;`)."""
    out: dict[str, str] = {}
    comment = re.compile(r"^\s*;")
    line = re.compile(r"^\s*(.+?)\s*=(.*)")
    for ln in text.splitlines():
        if not ln.strip() or comment.match(ln): continue
        m = line.match(ln)
        if m:
            out[m.group(1).strip()] = m.group(2).strip()
    return out


def build_faction_identifiers() -> dict[str, str]:
    """Parse Faction.cs for `public static Faction <field> = Get("<ident>");`
    Returns field → identifier (e.g. "gold" → "Gold")."""
    src = (DECOMP / "Source.Galaxy/Faction.cs").read_text()
    out: dict[str, str] = {}
    for m in re.finditer(r'public\s+static\s+Faction\s+(\w+)\s*=\s*Get\(\s*"([^"]+)"\s*\)', src):
        out[m.group(1)] = m.group(2)
    return out


def evaluate_text_expr(expr: str, name_map: dict[str, str],
                       translations: dict[str, str],
                       factions: dict[str, str]) -> str | None:
    """Evaluate a C# string-concat expression. Handles:
       - String literals: "..."
       - Character names: <field>.name
       - Translation with literal key: Translation.Translate("@KEY")
       - Translation with faction name: Translation.Translate(Faction.<field>.name)

       Returns the concatenated string, or None if any token is unresolvable."""
    expr = expr.strip()

    # Tokenize on + at depth 0
    tokens: list[str] = []
    depth = 0; in_str = False; escape = False
    buf: list[str] = []
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
        # Literal
        lit = re.fullmatch(r'"((?:\\.|[^"\\])*)"', t)
        if lit:
            parts.append(unescape_cs(lit.group(1)))
            continue
        # Character.name
        nm = re.fullmatch(r'(\w+)\.name', t)
        if nm and nm.group(1) in name_map:
            parts.append(name_map[nm.group(1)])
            continue
        # Translation.Translate("@KEY")
        tl_lit = re.fullmatch(r'Translation\.Translate\(\s*"@?([^"]+)"\s*\)', t)
        if tl_lit:
            key = tl_lit.group(1)
            if key in translations:
                parts.append(translations[key])
                continue
            return None
        # Translation.Translate(Faction.<field>.name)
        tl_fac = re.fullmatch(r'Translation\.Translate\(\s*Faction\.(\w+)\.name\s*\)', t)
        if tl_fac:
            field = tl_fac.group(1)
            if field in factions:
                key = "FactionName" + factions[field]
                if key in translations:
                    parts.append(translations[key])
                    continue
            return None
        # Unresolvable
        return None
    return "".join(parts)


def extract_file(path: Path, name_map, translations, factions) -> list[dict]:
    src = path.read_text()
    rel = str(path.relative_to(DECOMP))
    results: list[dict] = []
    for m in re.finditer(r'\bcDL\s*\(', src):
        open_paren = m.end() - 1
        close_paren = balance_parens(src, open_paren)
        if close_paren < 0: continue
        args = src[open_paren + 1:close_paren]
        parts = split_top_level_commas(args)
        if len(parts) < 2: continue
        speaker_expr = parts[0].strip()
        text_expr = parts[1].strip()
        text = evaluate_text_expr(text_expr, name_map, translations, factions)
        if text is None or not text.strip(): continue
        line = src[:m.start()].count("\n") + 1
        results.append({"file": rel, "speaker": speaker_expr, "text": text, "line": line})
    return results


def main():
    name_map = build_character_name_map()
    name_map.update({
        "canisecConquestCommander":  "Cade Callahan",
        "kolyatovConquestCommander": "Mikhail Kolyatov",
        "luminateConquestCommander": "Triane Solis",
        "stellarConquestCommander":  "Victor Hale",
    })
    print(f"Character names: {len(name_map)}")

    translations = load_translations()
    print(f"Translations: {len(translations)} keys from en-US TextAsset")

    factions = build_faction_identifiers()
    print(f"Faction identifiers: {len(factions)}")

    all_lines: list[dict] = []
    for f in DIALOGUE_FILES:
        path = DECOMP / f
        if not path.exists(): continue
        lines = extract_file(path, name_map, translations, factions)
        print(f"  {f}: {len(lines)}")
        all_lines.extend(lines)

    OUT.write_text(json.dumps(all_lines, indent=2, ensure_ascii=False))
    print(f"\nTotal: {len(all_lines)} lines → {OUT}")


if __name__ == "__main__":
    main()
