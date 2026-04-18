"""Shared path helpers for the prerender toolchain.

Single source of truth for the on-disk layout:

    prerender/
      manifest.json
      <speaker>/<sha>.ogg               ← shipped audio
      variants/<speaker>/<sha>.wav      ← debug WAVs before OGG encoding

Speaker names are sanitized via `sanitize_speaker()` to filesystem-safe folder
names (spaces → underscores, special chars → underscores).
"""
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path("/home/fank/repo/vanguard-galaxy")
PACK = ROOT / "prerender"
VARDIR = PACK / "variants"
MANIFEST = PACK / "manifest.json"


def sanitize_speaker(name: str) -> str:
    """Filesystem-safe speaker folder name. Preserves alnum, underscore, dash,
    period; replaces anything else (spaces, slashes, etc.) with underscore."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", name or "_unknown")


def ogg_path(speaker: str, key: str) -> Path:
    """Absolute path for a shipped OGG file under prerender/<speaker>/<key>.ogg."""
    return PACK / sanitize_speaker(speaker) / f"{key}.ogg"


def wav_path(speaker: str, key: str) -> Path:
    """Absolute path for a debug variant WAV under prerender/variants/<speaker>/<key>.wav."""
    return VARDIR / sanitize_speaker(speaker) / f"{key}.wav"


def manifest_ogg_rel(speaker: str, key: str) -> str:
    """Relative path stored in the manifest's `ogg` field — used by the C# plugin
    to locate the shipped file. Must be forward-slash regardless of OS."""
    return f"{sanitize_speaker(speaker)}/{key}.ogg"
