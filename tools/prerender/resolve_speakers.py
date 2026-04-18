#!/usr/bin/env python3
"""Improved speaker resolver. Handles Characters.cs factory pattern properly."""
from __future__ import annotations
import json, re
from pathlib import Path
from collections import Counter, defaultdict

DECOMP = Path("/tmp/decomp")
LINES = json.load(open("/tmp/resolved_lines.json"))
# Reset resolution
for l in LINES:
    l.pop("resolved_speaker", None)
    l.pop("resolution", None)

characters_src = (DECOMP / "Source.Dialogues/Characters.cs").read_text()

# ---- Build getter → NPC (for explicit speaker refs) -----------------------

# Static fields: `public static Character captain;` etc
# These are assigned elsewhere (CreateCaptain / CreateShipAI)
# Name-casing alone isn't enough — we need to know who they represent.
# captain = player character (variable name). shipAi = ECHO.
static_names = {
    "captain": "captain",       # player captain; voice will be picked at render
    "shipAi":  "ECHO",
    # Typo in source content files — the actual field is "steelVulture..."
    "steelVutureComputerSalesman": "Thundo Klipz",
    # Procedural / generic salesmen & crew members — no specific NPC name
    "procedural_salesman": "_generic_salesman",
    "procedural_crew":     "_generic_crew",
}

# Property pattern:
#   public static Character greg => _greg ?? (_greg = Greg());
# Capture property name + factory method name
prop_to_factory = {}
for m in re.finditer(
    r'public\s+static\s+Character\s+(\w+)\s*=>\s*\w+\s*\?\?\s*\(\w+\s*=\s*(\w+)\(\)\)',
    characters_src,
):
    prop_to_factory[m.group(1)] = m.group(2)

# Factory pattern:
#   public static Character Greg() { ... CreateCharacter("Greg") ... }
# Capture factory name + character name
factory_to_npc = {}
# Non-greedy body capture that stops at first `return character;` or next `public static`
# Simpler: grab the whole function via brace matching.
def extract_functions(src: str):
    out = {}
    i = 0
    while True:
        m = re.search(r'public\s+static\s+Character\s+(\w+)\s*\(\s*(?:Faction\s+\w+)?\s*\)\s*\{', src[i:])
        if not m: break
        func_name = m.group(1)
        start = i + m.end() - 1  # position of opening brace
        # brace-match
        depth = 0
        j = start
        while j < len(src):
            if src[j] == '{': depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0: break
            j += 1
        body = src[start+1:j]
        out[func_name] = body
        i = j + 1
    return out

funcs = extract_functions(characters_src)
print(f"Found {len(funcs)} static Character factory functions")

# Resolve conquest-commander translation keys
conquest_names = {
    "ConquestCanisecCommander":  "Cade Callahan",
    "ConquestStellarCommander":  "Victor Hale",
    "ConquestKolyatovCommander": "Mikhail Kolyatov",
    "ConquestLuminateCommander": "Triane Solis",
}

for func_name, body in funcs.items():
    m = re.search(r'CreateCharacter\(\s*"([^"]+)"', body)
    if m:
        factory_to_npc[func_name] = m.group(1)
        continue
    tk = re.search(r'CreateCharacter\(\s*Translation\.Translate\("@(\w+)"', body)
    if tk:
        factory_to_npc[func_name] = conquest_names.get(tk.group(1), f"<key:{tk.group(1)}>")

print(f"factory → NPC: {len(factory_to_npc)}")

# Compose: speaker identifier (as used in content files) → NPC name
speaker_to_npc = dict(static_names)
for prop, factory in prop_to_factory.items():
    if factory in factory_to_npc:
        speaker_to_npc[prop] = factory_to_npc[factory]

# Also: some content files use `captain` / lowercase directly, already covered.
# Static fields' names themselves — add
for fname in re.findall(r'private\s+static\s+Character\s+_(\w+);', characters_src):
    # _greg, etc. The public property is `greg` which lazy-inits.
    pass  # already handled via prop_to_factory

# Dump the map for inspection
print(f"\nspeaker_to_npc: {len(speaker_to_npc)} entries")
for k, v in sorted(speaker_to_npc.items()):
    print(f"  {k:<40s} -> {v}")

# ---- Build dialogue-method → NPC (for `character` local param) -------------

# For each factory function body, find registered dialogue methods:
#   character.createDialogue = SomeClass.Method;
#   character.AddDialogue(trigger, SomeClass.Method);
#   character.AddDefaultDialogue(SomeClass.Method(character));
method_to_npc = defaultdict(list)
for func_name, body in funcs.items():
    npc = factory_to_npc.get(func_name)
    if not npc:
        continue
    # createDialogue = X.Y.Method;
    for mm in re.finditer(r'character\.createDialogue\s*=\s*(?:[\w.]+\.)?(\w+)\s*;', body):
        method_to_npc[mm.group(1)].append(npc)
    # AddDialogue(trigger, X.Y.Method) — method name is the last identifier before closing paren
    for mm in re.finditer(r'character\.AddDialogue\([^,]+,\s*(?:[\w.]+\.)?(\w+)\s*\)', body):
        method_to_npc[mm.group(1)].append(npc)
    # AddDialogue(MissionIds.X, c => ContentClass.Method(c).dialogues(), ...)
    for mm in re.finditer(r'c\s*=>\s*(?:[\w.]+\.)?(\w+)\s*\(\s*c\s*\)\s*\.\s*dialogues', body):
        method_to_npc[mm.group(1)].append(npc)
    # AddDefaultDialogue(X.Method(character))
    for mm in re.finditer(r'AddDefaultDialogue\(\s*(?:[\w.]+\.)?(\w+)\s*\(\s*character\s*\)', body):
        method_to_npc[mm.group(1)].append(npc)
    # character.createDialogue = (Character c) => SideMissions.CreatePatrolDialogue(c);
    for mm in re.finditer(r'createDialogue\s*=\s*\(\s*Character\s+c\s*\)\s*=>\s*(?:[\w.]+\.)?(\w+)\s*\(\s*c\s*\)', body):
        method_to_npc[mm.group(1)].append(npc)

print(f"\nmethod → NPC: {len(method_to_npc)}")
for method, npcs in sorted(method_to_npc.items())[:20]:
    unique = sorted(set(npcs))
    print(f"  {method:<45s} -> {unique}")

# ---- Now resolve each dialogue line ---------------------------------------

# Strip "Characters." prefix for lookup
def normalize_speaker(sp):
    sp = sp.strip()
    sp = re.sub(r"^Characters\.", "", sp)
    return sp

# For each line, if speaker is an explicit name → lookup. If "character" → enclosing method.
# For the latter, parse the file once to find each method's span.
file_methods = {}  # file -> list of (start_offset, end_offset, method_name)
for file_rel in {l["file"] for l in LINES}:
    src = (DECOMP / file_rel).read_text()
    methods = []
    # Public methods returning Dialogue or List<DialogueLine>
    for m in re.finditer(
        r'public\s+(?:static\s+)?(?:Dialogue|List<DialogueLine>)\s+(\w+)\s*\([^)]*\)\s*\{',
        src,
    ):
        # Brace-match from opening brace
        start = m.end() - 1
        depth = 0; j = start
        while j < len(src):
            if src[j] == '{': depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0: break
            j += 1
        methods.append((start, j, m.group(1)))
    file_methods[file_rel] = methods

for line in LINES:
    sp_norm = normalize_speaker(line["speaker"])

    if sp_norm in speaker_to_npc:
        line["resolved_speaker"] = speaker_to_npc[sp_norm]
        line["resolution"] = "explicit"
        continue

    if sp_norm in ("character", "questgiver", "c"):
        # Special-case: patrons files use `character` but the character is procedural
        if "Station.Patrons" in line["file"]:
            line["resolved_speaker"] = ("_generic_salesman" if "Salesman" in line["file"]
                                        else "_generic_crew")
            line["resolution"] = "procedural"
            continue
        # find enclosing method in file
        src = (DECOMP / line["file"]).read_text()
        # find line text position (approximate)
        esc = re.escape(line["text"])
        m = re.search(esc, src)
        if not m:
            line["resolved_speaker"] = f"<text-not-found>"
            line["resolution"] = "local_param_unresolved"
            continue
        pos = m.start()
        # find method containing pos
        method_name = None
        for start, end, name in file_methods.get(line["file"], []):
            if start <= pos <= end:
                method_name = name
                break
        if method_name and method_name in method_to_npc:
            candidates = sorted(set(method_to_npc[method_name]))
            if len(candidates) == 1:
                line["resolved_speaker"] = candidates[0]
                line["resolution"] = "local_param_resolved"
            else:
                line["resolved_speaker"] = candidates[0]  # pick first
                line["resolution"] = f"local_param_ambiguous({','.join(candidates)})"
        else:
            line["resolved_speaker"] = f"<method:{method_name}>"
            line["resolution"] = "local_param_unresolved"
        continue

    # Anything else (e.g. explicit "captain", "greg" bare words) - fall to speaker_to_npc
    line["resolved_speaker"] = sp_norm
    line["resolution"] = "raw_identifier"

# Stats
res_counts = Counter(l["resolution"] for l in LINES)
print(f"\n=== Resolution counts ===")
for k, v in sorted(res_counts.items(), key=lambda kv: -kv[1]):
    print(f"  {v:4d}  {k}")

unresolved = [l for l in LINES if str(l.get("resolved_speaker","")).startswith("<")]
print(f"\nUnresolved: {len(unresolved)}")
for l in unresolved[:5]:
    print(f"  file={l['file']}  speaker={l['speaker']!r}  -> {l['resolved_speaker']}")

speaker_counts = Counter(l["resolved_speaker"] for l in LINES)
print(f"\nTop 30 resolved speakers:")
for sp, n in speaker_counts.most_common(30):
    print(f"  {n:4d}  {sp}")

Path("/tmp/resolved_lines.json").write_text(json.dumps(LINES, indent=2, ensure_ascii=False))
print(f"\nSaved /tmp/resolved_lines.json")
