# Third-Party Notices

Vanguard Galaxy TTS bundles or depends on the following third-party components.
Each is distributed under its own license, reproduced or linked below.

## Runtime dependencies (shipped inside the mod)

### Kokoro v1.0 multi-lang
- **Project:** https://huggingface.co/hexgrad/Kokoro-82M
- **License:** Apache License 2.0
- **What we ship:** `model.onnx`, `voices.bin`, `tokens.txt`, `lexicon-us-en.txt`,
  `espeak-ng-data/` (inside `tools/kokoro/`). Pretrained neural TTS model with
  53 multilingual speaker embeddings — the voice of every NPC in this mod.

### sherpa-onnx
- **Project:** https://github.com/k2-fsa/sherpa-onnx
- **License:** Apache License 2.0
- **What we ship:** `sherpa-onnx-offline-tts.exe` (renamed to `sherpa-onnx-tts.exe`
  inside `tools/sherpa/`). Windows CLI binary that drives Kokoro ONNX inference
  at runtime for live-TTS fallback.

### BepInEx 5
- **Project:** https://github.com/BepInEx/BepInEx
- **License:** LGPL 2.1
- **What we depend on:** The mod loader framework. Not bundled — users install it
  separately. VGTTS targets BepInEx 5.4.x via `netstandard2.1`.

### HarmonyX
- **Project:** https://github.com/BepInEx/HarmonyX
- **License:** MIT
- **What we depend on:** Runtime method patching. Pulled transitively through
  BepInEx; not bundled in this mod's redistributable.

## Build-time tools (not shipped in the release zip)

### BepInEx.AssemblyPublicizer
- **Project:** https://github.com/BepInEx/BepInEx.AssemblyPublicizer
- **License:** MIT
- **Use:** Generates a "publicized" reference copy of the game's
  `Assembly-CSharp.dll` — method signatures only, no IL bodies — committed
  at `VGTTS/lib/Assembly-CSharp.dll` so CI can compile VGTTS without the
  proprietary game code. The real game assembly takes over at runtime.


### F5-TTS
- **Project:** https://github.com/SWivid/F5-TTS
- **License:** MIT
- **Use:** Originally used for voice cloning during early pack development.
  Fully removed from the release pipeline in v1.2.0; no F5 artifacts remain
  in shipped OGGs.

### UnityPy
- **Project:** https://github.com/K0lb3/UnityPy
- **License:** MIT
- **Use:** Read the game's `resources.assets` at extraction time to resolve
  `Translation.Translate(...)` calls to their en-US strings. Not shipped.

## Game content

Dialogue text, character names, and portraits in this mod are derived from
**Vanguard Galaxy** by Bat Roost Games. Their use here is intended to support
the modding community and remains subject to the game's EULA. The mod ships
pre-rendered **audio** of those lines; the lines themselves are not redistributed
as text.
