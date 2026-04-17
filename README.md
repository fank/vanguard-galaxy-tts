# Vanguard Galaxy TTS (VGTTS)

BepInEx plugin that speaks dialogue lines in Vanguard Galaxy using text-to-speech.

Strategy: **hybrid** — pre-rendered voice lines for known dialogue, live TTS fallback with on-disk caching for anything unseen. Per-character voice mapping.

## Status

Early scaffold. Current milestone: logs every dialogue line to the BepInEx console to verify the Harmony hook fires correctly. No audio yet.

## Requirements

- Vanguard Galaxy (Steam)
- [BepInEx 5.x](https://github.com/BepInEx/BepInEx/releases) installed into the game folder
- .NET SDK 8+ for building (on WSL, the Makefile auto-detects a local install at `/tmp/dnsdk/dotnet`)

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
