#!/usr/bin/env python3
"""Extract NPC portrait sprites from Unity assets.

Each Character has a portretSprite loaded via Resources.Load<Sprite>("Sprites/NPC/X").
In Unity's resources.assets / sharedassets*.assets, these are Texture2D + Sprite
pairs. We extract the underlying texture as PNG.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import UnityPy

GAME_DATA = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Vanguard Galaxy/VanguardGalaxy_Data")
NPCS = json.load(open("/tmp/npcs.json"))
# Build set of portrait names we want
wanted = {n["portrait"] for n in NPCS}
print(f"Looking for {len(wanted)} portraits: {sorted(wanted)}\n")

OUTDIR = Path("/home/fank/repo/vanguard-galaxy/tools/prerender/npc_portraits")
OUTDIR.mkdir(parents=True, exist_ok=True)

found = {}

# Scan all candidate asset files
asset_files = list(GAME_DATA.glob("resources.assets")) + \
              sorted(GAME_DATA.glob("sharedassets*.assets"))
print(f"Scanning {len(asset_files)} asset files...\n")

for af in asset_files:
    try:
        env = UnityPy.load(str(af))
    except Exception as e:
        print(f"  skip {af.name}: {e}")
        continue
    for obj in env.objects:
        # Textures backing Sprites
        if obj.type.name != "Texture2D":
            continue
        try:
            data = obj.read()
        except Exception:
            continue
        name = getattr(data, "m_Name", None) or ""
        if name not in wanted:
            continue
        try:
            img = data.image
            if img is None:
                continue
            out = OUTDIR / f"{name}.png"
            img.save(str(out))
            found[name] = (af.name, out.stat().st_size)
            print(f"  {name:<30s}  {img.size[0]}x{img.size[1]}  from {af.name}")
        except Exception as e:
            print(f"  {name}: failed to save ({e})")

missing = wanted - set(found)
print(f"\nExtracted: {len(found)} / {len(wanted)}")
if missing:
    print(f"Missing: {sorted(missing)}")
