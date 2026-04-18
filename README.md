# Vanguard Galaxy TTS (VGTTS)

BepInEx plugin that speaks dialogue lines in Vanguard Galaxy using text-to-speech.

Strategy: **pre-rendered pack primary, offline TTS fallback.** The 66 known ECHO travel tips are synthesized once (GPU, F5-TTS with Kokoro-cloned British female) at build time, encoded as OGG Vorbis, and shipped with the plugin. At runtime, dialogue lines hit the pack first; anything not in the pack (new lines from future game patches) falls through to live Kokoro TTS.

Benefits of the tiered design:
- Every shipped ECHO line has the voice, prosody, and emotional contour we picked offline with unlimited compute budget
- Forward-compatible with game patches (new text works, just sounds different)
- Fast: OGG load is ~100 ms vs. ~3-5 s for live Kokoro synth on cold start

## Status

Early scaffold. Current milestone: logs every dialogue line to the BepInEx console to verify the Harmony hook fires correctly. No audio yet.

## Requirements

- Vanguard Galaxy (Steam)
- [BepInEx 5.x](https://github.com/BepInEx/BepInEx/releases) installed into the game folder (`make install-bepinex`)
- .NET SDK 8+ for building
- ~1.1 GB free for the bundled Kokoro + Piper voice models

## One-shot setup

```bash
make install-bepinex        # downloads + unpacks BepInEx into the game folder
make download-tools         # fetches piper + sherpa + Kokoro v1.0 (~1 GB total)
make deploy                 # builds and copies everything into BepInEx/plugins/
```

## Build + deploy (WSL)

```bash
make deploy
```

This:
1. Symlinks the game's `Assembly-CSharp.dll` into `VGTTS/lib/` for compile-time references
2. Builds the plugin
3. Copies the DLL into `<game>/BepInEx/plugins/`

If your Steam install is elsewhere, set `GAME_DIR` on the command line:

```bash
make deploy GAME_DIR="/mnt/d/SteamLibrary/steamapps/common/Vanguard Galaxy"
```

## First-run verification

1. Launch the game once with BepInEx installed (creates `BepInEx/` subfolders)
2. `make deploy`
3. Launch the game, open the BepInEx console (enable via `BepInEx/config/BepInEx.cfg` → `[Logging.Console]` → `Enabled = true`)
4. Talk to any NPC — every dialogue line should print as `[dialogue] Name: "..."`

## Architecture (planned)

```
VGTTS/
├── Plugin.cs                 BepInEx entry, applies patches
├── Patches/                  Harmony hooks into DialogueManager
├── TTS/                      ITtsProvider + SAPI / Piper / cloud implementations
├── Audio/                    byte[] → Unity AudioClip, routed through SoundBuilder
├── Cache/                    sha256(text+voice) → .wav on disk
├── Voice/                    Character.name → voice config mapping
└── Config/                   BepInEx ConfigFile bindings
```
