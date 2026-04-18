#!/usr/bin/env python3
"""Parse Characters.cs to extract every NPC's name, description, and portrait path.

Pattern per call site:
    Character.CreateCharacter("Name")
        .WithDescription("Some role/title")
        .WithPortret(Resources.Load<Sprite>("Sprites/NPC/Folder"));

Some names come from Translation.Translate("@ConquestXCommander") — we record
the translation key rather than the resolved name (it's locale-dependent anyway).
"""
from __future__ import annotations
import re, json
from pathlib import Path

SRC = Path("/tmp/decomp/Characters.cs").read_text()

# Lenient regex: CreateCharacter(...) ... WithDescription(...) ... WithPortret(...)
# Allow the arguments to be either "string literal" or Translation.Translate("@Key")
STRING_OR_KEY = r'(?:"((?:[^"\\]|\\.)*)"|Translation\.Translate\("(@[^"]+)"\))'
PORTRET_PATH = r'"Sprites/NPC/([^"]+)"'
PATTERN = re.compile(
    rf'Character\.CreateCharacter\(\s*{STRING_OR_KEY}\s*\)\s*'
    rf'(?:\.WithDescription\(\s*{STRING_OR_KEY}\s*\))?\s*'
    rf'\.WithPortret\(\s*Resources\.Load<Sprite>\(\s*{PORTRET_PATH}\s*\)\s*\)',
    re.DOTALL,
)

npcs = []
for m in PATTERN.finditer(SRC):
    name_lit, name_key, desc_lit, desc_key, portrait = m.groups()
    name = name_lit if name_lit is not None else f"<key:{name_key}>"
    desc = desc_lit if desc_lit is not None else (f"<key:{desc_key}>" if desc_key else None)
    npcs.append({"name": name, "description": desc, "portrait": portrait})

print(f"Extracted {len(npcs)} NPCs\n")
for n in npcs:
    desc = n["description"] or "-"
    print(f"  {n['name']:<32s}  {n['portrait']:<30s} {desc}")

Path("/tmp/npcs.json").write_text(json.dumps(npcs, indent=2, ensure_ascii=False))
print(f"\nSaved /tmp/npcs.json ({len(npcs)} entries)")
