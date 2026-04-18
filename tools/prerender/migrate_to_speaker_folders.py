#!/usr/bin/env python3
"""One-shot migration: flat prerender/echo/ → speaker-folder layout.

Before:
    prerender/echo/manifest.json
    prerender/echo/<sha>.ogg × 1238
    prerender/echo/variants/<sha>.wav × N

After:
    prerender/manifest.json
    prerender/<speaker>/<sha>.ogg
    prerender/variants/<speaker>/<sha>.wav

Speaker names are sanitized to filesystem-safe folders (spaces → underscores).
Idempotent — safe to re-run; files already in the target are left alone.
"""
from __future__ import annotations
import json, re, shutil, sys
from pathlib import Path

ROOT = Path("/home/fank/repo/vanguard-galaxy")
OLD = ROOT / "prerender" / "echo"
NEW = ROOT / "prerender"


def sanitize_speaker(name: str) -> str:
    """Filesystem-safe speaker folder name. Preserves alnum, underscore, dash,
    period; replaces anything else (spaces, slashes) with underscore."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "_unknown")


def main():
    manifest_old = OLD / "manifest.json"
    manifest_new = NEW / "manifest.json"
    variants_old = OLD / "variants"
    variants_new = NEW / "variants"

    if not manifest_old.exists() and manifest_new.exists():
        print(f"Already migrated ({manifest_new} exists, {manifest_old} does not).")
        return

    manifest = json.loads(manifest_old.read_text())
    print(f"Loaded manifest: {len(manifest)} entries")

    # Plan moves
    speakers = set()
    moves_ogg = []
    moves_wav = []
    for key, entry in manifest.items():
        speaker = entry.get("speaker", "_unknown")
        sdir = sanitize_speaker(speaker)
        speakers.add(sdir)

        old_ogg = OLD / f"{key}.ogg"
        new_ogg = NEW / sdir / f"{key}.ogg"
        moves_ogg.append((old_ogg, new_ogg, sdir))

        old_wav = variants_old / f"{key}.wav"
        if old_wav.exists():
            new_wav = variants_new / sdir / f"{key}.wav"
            moves_wav.append((old_wav, new_wav))

        # Rewrite ogg path in manifest entry to be speaker-relative
        entry["ogg"] = f"{sdir}/{key}.ogg"

    print(f"Creating {len(speakers)} speaker dirs")
    for sdir in sorted(speakers):
        (NEW / sdir).mkdir(parents=True, exist_ok=True)
        (variants_new / sdir).mkdir(parents=True, exist_ok=True)

    # Execute moves
    missing_ogg = 0
    moved_ogg = 0
    for old, new, _ in moves_ogg:
        if old.exists():
            shutil.move(str(old), str(new))
            moved_ogg += 1
        elif not new.exists():
            missing_ogg += 1
    print(f"Moved {moved_ogg}/{len(moves_ogg)} OGGs (missing: {missing_ogg})")

    moved_wav = 0
    for old, new in moves_wav:
        if old.exists():
            shutil.move(str(old), str(new))
            moved_wav += 1
    print(f"Moved {moved_wav} variant WAVs")

    # Write new manifest, delete old one
    manifest_new.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"Wrote {manifest_new}")

    # Cleanup: old echo/ and old variants/ should be empty now
    manifest_old.unlink()
    if variants_old.exists():
        leftover = list(variants_old.rglob("*"))
        if leftover and any(p.is_file() for p in leftover):
            print(f"WARNING: {variants_old} still has {sum(1 for p in leftover if p.is_file())} files — NOT removing")
        else:
            shutil.rmtree(variants_old)
            print(f"Removed empty {variants_old}")

    leftover = list(OLD.rglob("*"))
    if leftover and any(p.is_file() for p in leftover):
        print(f"WARNING: {OLD} still has {sum(1 for p in leftover if p.is_file())} files — NOT removing")
    else:
        shutil.rmtree(OLD)
        print(f"Removed empty {OLD}")

    print(f"\nDone. Sanity: {len(manifest)} entries across {len(speakers)} speakers.")


if __name__ == "__main__":
    main()
