# Nexus mod page — copy & paste source

Paste into the Nexus form fields when creating/updating the mod page.

---

## Mod title

**Vanguard Galaxy TTS — Neural Voices for Every NPC**

## Short description (180 char limit)

Neural text-to-speech for every dialogue line. 2831 pre-rendered clips cover every story line; 42+ NPCs get distinct voices. ECHO, your captain, and the whole cast get spoken.

## Category

- **Primary:** Audio / Voice
- **Secondary:** Gameplay

## Tags

`BepInEx` `voice` `tts` `audio` `dialogue` `immersion` `accessibility`

## Long description (markdown)

```markdown
## Voices for every dialogue line

Vanguard Galaxy is a text-heavy game — the dialogue is great, but reading it is the only way to hear it. This mod changes that: every line spoken by ECHO, the player captain, and all 42+ named NPCs gets a neural-synthesized voice, pre-rendered at build time and shipped with the mod.

### What you get

- **2831 pre-rendered OGG clips** covering every story and side-quest line the game currently has
- **42+ NPCs each with their own voice** — Japanese, Hindi, Spanish, French, Portuguese accents where the character calls for it (Stella Chion, Arle, Amalia Rodriguez, Claude, Oron, etc.)
- **6 captain voice presets** selectable in config (3 male + 3 female)
- **ECHO** gets a smooth, fatigue-resistant voice designed for the 200th playback (she talks *a lot*)
- **Live fallback** for anything the pack misses — dynamic commander-name lines, post-patch additions, procedural station names

### Install

1. Install **BepInEx 5.x** into your Vanguard Galaxy folder
2. Launch the game once so BepInEx creates its subfolders
3. Download and unzip this mod's contents into the game folder
4. Launch the game and talk to someone

Full install guide and troubleshooting in the README.

### Configuration

The mod creates `BepInEx/config/dev.fankserver.vgtts.cfg` on first launch. Key settings:

- `[General] Enabled` / `DialogueTTS` / `EchoTTS` — master toggles
- `[Voice] CaptainPreset` — `auto` / `m1..m3` / `f1..f3` — pick your captain's voice
- `[Voices]` — per-NPC voice overrides using Kokoro speaker IDs

### Requirements

- **Vanguard Galaxy** (Steam)
- **BepInEx 5.4.x** (free, open-source, install separately)
- **~500 MB disk space** for the neural TTS model + pre-rendered audio
- **Windows** (mod wraps sherpa-onnx's Windows binary)

### Known limitations

- Procedural station names ("The Oracle Spire", etc.) fall through to live TTS
- Scottish accent for Elias McIntire is a stand-in American voice (Kokoro has no Scottish speaker)
- Game patches adding new dialogue miss the pack until the community ships a delta

### Credits & licensing

This mod bundles Kokoro v1.0 (Apache 2.0), sherpa-onnx (Apache 2.0), and depends on BepInEx 5 (LGPL 2.1). The mod itself is MIT-licensed. Full attribution in `THIRD_PARTY_NOTICES.md` included in the download.

Game dialogue text, character names, and voice casting are derived from Vanguard Galaxy by Bat Roost Games; use here supports the modding community and remains subject to the game's EULA.

### Source & contributions

GitHub: [fank/vanguard-galaxy-tts](https://github.com/fank/vanguard-galaxy-tts)

When the game patches add new dialogue, contributions for the delta render are welcome — instructions in the README.
```

## Permissions (Nexus standard questions)

- **Upload permission:** You are not allowed to upload this file to other sites under any circumstances
- **Modification permission:** You are allowed to modify my files and release bug fixes or improve on the features without permission from or credit to me
- **Conversion permission:** You are not allowed to convert this file to work on other games under any circumstances
- **Asset use permission:** You are allowed to use the assets in this file without permission or crediting me
- **Asset use permission in mods/files that are being sold:** You are not allowed to use assets from this file in any mods/files that are being sold, for money, on Steam Workshop or other platforms
- **Asset use permission in mods/files that earn donation points:** You are allowed to earn Donation Points for your mods if they use my assets

(Adjust based on your own preference — the defaults above are restrictive on redistribution, permissive on derivative mods.)

## Images / screenshots / video ideas

The mod has no UI — it's audio-only. Good content for the page:
- **Hero image:** a title card with the mod name over a screenshot of the game's dialogue UI
- **Before/after video:** 30-60 sec clip showing a key story beat (e.g. ECHO's first monologue, the captain meeting Raythor) with captions
- **Voice sampler video:** a montage of 8-10 NPCs each saying one line, with their names captioned
- **Config screenshot:** the `.cfg` file highlighting `CaptainPreset` options

## Version / changelog entry (for the Nexus version field)

**v1.2.0** — Kokoro-only, full captain presets, auto config migration from v1.1
