#!/usr/bin/env python3
"""Verify Python normalizer output == C# normalizer output for every ECHO tip.

A mismatch at runtime = cache miss = prerender doesn't kick in = user hears
live-TTS fallback quality. This test prevents regressions in the normalizer pair.

Runs the Python normalizer over every tip + compares to a reference list that
must be produced by a tiny C# harness (see tools/prerender/cs_parity/).

For now, just computes keys and reports them so a separate C# test can diff.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import for_tts, prerender_key  # noqa

tips = json.load(open(Path(__file__).parent / "echo_tips.json"))
print(f"tip_id\traw\tnormalized\tkey")
for k, v in sorted(tips.items()):
    v = v.strip()
    n = for_tts(v)
    key = prerender_key(v, "ECHO")
    print(f"{k}\t{v!r}\t{n!r}\t{key}")
