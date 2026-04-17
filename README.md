# Vanguard Galaxy TTS (VGTTS)

BepInEx plugin that speaks dialogue lines in Vanguard Galaxy using text-to-speech.

Strategy: offline neural TTS (Kokoro v1.0 primary, Piper as optional fallback) with on-disk caching and per-character voice profiles.

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
