# Autopilot ETA-Sync + Arrival Snap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the autopilot (IdleManager) task cycle complete exactly when space travel ends, eliminating the 0–12s idle wait after every arrival, and repurpose the green progress circle as a live travel-ETA indicator.

**Architecture:** Two Harmony patches in a new `AutopilotTimingPatches.cs` file. (1) **ETA-sync**: a Postfix on `IdleManager.Update` overwrites `updateTimer`/`updateTimerBase` with live `remainingDistance / travelSpeed` while `TravelManager.Instance.isWarping`. (2) **Arrival-snap**: a Postfix on `TravelManager.TravelToNextWaypoint` zeroes `updateTimer` when the final waypoint is reached (covers jump-gate transitions where ETA math is unavailable). Both patches are gated by new BepInEx config entries and only engage while `GamePlayer.current.autoPlay` is true. Private setters on `IdleManager` auto-properties are reached via `AccessTools.FieldRefAccess` against the compiler-generated backing fields.

**Tech Stack:** C# netstandard2.1, BepInEx 5.x, HarmonyX 2.10, Unity 6000.2.6 (Mono backend). No test framework — verification is in-game against the BepInEx console and the autopilot tab's green/orange fill circle (`SideTabAutopilot.timerFill`).

**Verification model:** The VGTTS project has no automated tests. Each task ends with (a) a successful `make deploy`, and (b) a documented in-game acceptance check that the plan spells out step-by-step. Debug log lines (`Plugin.Log.LogDebug(...)`) are emitted at each hook point so the user can confirm the patch fired by watching the BepInEx console.

**Target file decomposition:**
- **Create** `VGTTS/Patches/AutopilotTimingPatches.cs` — the only new file; holds both patches, reflection accessors, and the pure ETA helper.
- **Modify** `VGTTS/Plugin.cs` — add three `ConfigEntry` bindings and one `PatchAll(typeof(Patches.AutopilotTimingPatches))` call. No other classes are touched.

---

## Task 1: Scaffold the patch file, config bindings, and Harmony registration

**Goal of this task:** Create the empty patch class, wire three BepInEx config entries, register the patches, and verify the plugin still loads in-game. No behavior change yet — this is a pure scaffolding step so later tasks can focus on logic.

**Files:**
- Create: `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs`
- Modify: `/home/fank/repo/vanguard-galaxy/VGTTS/Plugin.cs` (add config bindings around line 62 and the PatchAll call around line 78)

- [ ] **Step 1: Create the patch file with a logging stub**

Create `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs` with this exact content:

```csharp
using Behaviour.Gameplay;
using Behaviour.Managers;
using HarmonyLib;
using Source.Player;
using UnityEngine;

namespace VGTTS.Patches;

/// <summary>
/// Patches on <see cref="IdleManager"/> and <see cref="TravelManager"/> that align
/// the autopilot "next-task" cycle with space-travel arrival. Two mechanisms:
///   • <b>ETA-sync</b> (postfix on <c>IdleManager.Update</c>): while the ship is
///     warping, overwrite <c>updateTimer</c>/<c>updateTimerBase</c> with the live
///     travel ETA so the green progress circle visibly completes on drop-out.
///   • <b>Arrival-snap</b> (postfix on <c>TravelManager.TravelToNextWaypoint</c>):
///     when the final waypoint is reached, zero <c>updateTimer</c> so the next
///     <c>IdleManager.Update</c> tick immediately triggers <c>FindActivity</c>.
///
/// Both engage only when <c>GamePlayer.current.autoPlay</c> is true and the
/// matching config entry is enabled. Private setters on <c>IdleManager</c>'s
/// auto-properties are written via <see cref="AccessTools.FieldRefAccess"/>
/// against the C# compiler-generated backing fields.
/// </summary>
[HarmonyPatch]
internal static class AutopilotTimingPatches
{
    // Compiler-generated backing-field names for auto-properties on IdleManager.
    // If the game is ever recompiled with different property names, update these.
    private static readonly AccessTools.FieldRef<IdleManager, float> UpdateTimerRef =
        AccessTools.FieldRefAccess<IdleManager, float>("<updateTimer>k__BackingField");

    private static readonly AccessTools.FieldRef<IdleManager, float> UpdateTimerBaseRef =
        AccessTools.FieldRefAccess<IdleManager, float>("<updateTimerBase>k__BackingField");
}
```

- [ ] **Step 2: Add config bindings to Plugin.cs**

Open `/home/fank/repo/vanguard-galaxy/VGTTS/Plugin.cs`. Find the field declarations block near line 27–33. After the existing `ConfigEntry<string> CfgCaptainPreset = null!;` line, add three new fields:

```csharp
internal ConfigEntry<bool> CfgAutopilotTiming = null!;
internal ConfigEntry<bool> CfgAutopilotEtaSync = null!;
internal ConfigEntry<bool> CfgAutopilotArrivalSnap = null!;
```

Then in `Awake()`, after the `CfgCaptainPreset = Config.Bind(...)` block (ending around line 61), add:

```csharp
CfgAutopilotTiming = Config.Bind("Autopilot", "TimingEnabled", true,
    "Master enable for autopilot (IdleManager) timing tweaks. When false, both " +
    "ETA-sync and arrival-snap are skipped and the vanilla 12s cycle runs unchanged.");
CfgAutopilotEtaSync = Config.Bind("Autopilot", "EtaSync", true,
    "While warping, continuously set the IdleManager cycle to match the live travel ETA " +
    "(remainingDistance / travelSpeed). Makes the green progress circle complete exactly " +
    "on drop-out instead of running its own 12s loop during travel. Requires TimingEnabled.");
CfgAutopilotArrivalSnap = Config.Bind("Autopilot", "ArrivalSnap", true,
    "When the ship reaches its final waypoint, zero the IdleManager cycle timer so the " +
    "next task fires on the following Update tick instead of waiting up to 12s. Covers " +
    "jump-gate transitions where ETA is unavailable. Requires TimingEnabled.");
```

- [ ] **Step 3: Register the Harmony patch**

Still in `/home/fank/repo/vanguard-galaxy/VGTTS/Plugin.cs`, find the `_harmony.PatchAll(...)` block (around line 76–78). After the last existing `_harmony.PatchAll(typeof(Patches.CharactersPatches));` line, add:

```csharp
_harmony.PatchAll(typeof(Patches.AutopilotTimingPatches));
```

- [ ] **Step 4: Build to verify the plugin still compiles**

Run from `/home/fank/repo/vanguard-galaxy/`:

```bash
make build
```

Expected: build succeeds, produces `VGTTS/bin/Debug/netstandard2.1/VGTTS.dll`. No compiler errors. (A warning about "HarmonyPatch class contains no patches" is possible at this stage since we have no `[HarmonyPatch(...)]` methods yet — ignore it for this step.)

- [ ] **Step 5: Deploy and verify the plugin loads**

```bash
make deploy
```

Launch the game. Open the BepInEx console. Expect the standard load line:

```
[Info   :Vanguard Galaxy TTS] Vanguard Galaxy TTS v1.1.0 loaded (N patches)
```

where `N` matches the count of `PatchAll` calls (currently 4 with our addition, but the scaffold has no method-level patches yet so the reported patch count will match the previous value of 3 — this is expected for a scaffolding commit).

Also verify the new config entries are written to `BepInEx/config/dev.fankserver.vgtts.cfg` after first launch. Look for the `[Autopilot]` section with `TimingEnabled`, `EtaSync`, and `ArrivalSnap` keys.

- [ ] **Step 6: Commit**

```bash
git add VGTTS/Patches/AutopilotTimingPatches.cs VGTTS/Plugin.cs
git commit -m "feat: scaffold AutopilotTimingPatches with config bindings

Empty patch class plus three BepInEx config entries (TimingEnabled,
EtaSync, ArrivalSnap) and Harmony registration. No behavior change yet
— subsequent commits add the ETA-sync and arrival-snap patches."
```

---

## Task 2: Arrival-snap patch — zero the cycle timer on final waypoint

**Goal of this task:** When space travel ends at the final destination, immediately force the IdleManager's `updateTimer` to zero so `FindActivity()` fires on the next Update tick instead of waiting up to 12 seconds. This alone removes the "ship arrives, then waits 0–12s doing nothing" delay the user reported.

**Files:**
- Modify: `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs`

- [ ] **Step 1: Add the TravelToNextWaypoint postfix**

In `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs`, inside the `AutopilotTimingPatches` class after the two `FieldRef` declarations, add:

```csharp
    /// <summary>
    /// Postfix on <see cref="TravelManager.TravelToNextWaypoint"/>. The game
    /// invokes this at the end of every leg of a journey: if more waypoints
    /// remain, it starts the next leg; if the list is empty, travel ended.
    /// In the empty-list case, and only when the player is on autopilot, we
    /// zero <c>updateTimer</c> so the very next <see cref="IdleManager.Update"/>
    /// tick calls <c>FindActivity</c> — eliminating the residual 0–12s wait
    /// between drop-out and the next autonomous action.
    /// </summary>
    [HarmonyPostfix]
    [HarmonyPatch(typeof(TravelManager), nameof(TravelManager.TravelToNextWaypoint))]
    private static void TravelToNextWaypoint_Postfix()
    {
        if (!Plugin.Instance.CfgAutopilotTiming.Value) return;
        if (!Plugin.Instance.CfgAutopilotArrivalSnap.Value) return;

        var player = GamePlayer.current;
        if (player == null || !player.autoPlay) return;

        // The final-leg branch of TravelToNextWaypoint runs when waypoints is
        // empty and sets travelCoroutine = null. Guard on both so we don't
        // fire mid-journey between legs of a multi-jump trip.
        if (player.waypoints.Count != 0) return;

        var idle = Singleton<IdleManager>.Instance;
        if (idle == null) return;

        // TravelActive() also consults usingJumpgate. If a jump-gate coroutine
        // is still in flight (it calls TravelToNextWaypoint as its last line),
        // wait for it to finalize rather than firing early. In practice
        // TravelActive is already false by the time the postfix runs because
        // the orig method set travelCoroutine = null and usingJumpgate was
        // cleared before this invocation — but belt-and-braces.
        if (Singleton<TravelManager>.Instance.TravelActive()) return;

        Plugin.Log.LogDebug("[autopilot-timing] arrival-snap: zeroing updateTimer");
        UpdateTimerRef(idle) = 0f;
    }
```

You'll also need to add a `using` for `Behaviour.Util` at the top of the file (where `Singleton<T>` lives — note: `Behaviour.Util`, not `Source.Util`). The final `using` block should read:

```csharp
using Behaviour.Gameplay;
using Behaviour.Managers;
using Behaviour.Util;
using HarmonyLib;
using Source.Player;
using UnityEngine;
```

- [ ] **Step 2: Build and verify compilation**

```bash
cd /home/fank/repo/vanguard-galaxy && make build
```

Expected: build succeeds. The Harmony patch count reported on game launch should now include this method.

- [ ] **Step 3: Deploy**

```bash
cd /home/fank/repo/vanguard-galaxy && make deploy
```

- [ ] **Step 4: In-game verification**

1. Enable debug logging: edit `$GAME_DIR/BepInEx/config/BepInEx.cfg` → `[Logging.Console]` → set `LogLevels` to include `Debug` (or `All`).
2. Launch the game. Load a save where autopilot is unlocked.
3. Open the BepInEx console.
4. Press **T** to enable autopilot. Watch the side-panel "Autopilot" tab — the fill circle should turn green and start ticking.
5. Wait for the autopilot to pick a destination and start warping (you'll see `[autopilot-timing]` log lines are NOT expected yet — ETA-sync comes in Task 3).
6. When the ship drops out of warp at the destination POI, expect one console line:

    ```
    [Debug  :Vanguard Galaxy TTS] [autopilot-timing] arrival-snap: zeroing updateTimer
    ```

7. Visually: in the vanilla build, after drop-out the green circle would keep running up to ~12s before doing anything. With the patch, the circle should snap to empty and the next autopilot activity message (`@IdleCalculating` → `@IdleMining` / `@IdleDockWithSS` / etc.) should appear within one or two frames.
8. Disable the feature for a control test: edit `BepInEx/config/dev.fankserver.vgtts.cfg`, set `ArrivalSnap = false`, relaunch. The log line should NOT appear and the 0–12s vanilla wait should return. Re-enable after confirming.

- [ ] **Step 5: Commit**

```bash
git add VGTTS/Patches/AutopilotTimingPatches.cs
git commit -m "feat: autopilot arrival-snap — zero IdleManager updateTimer on final waypoint

Postfix on TravelManager.TravelToNextWaypoint: when the player is on
autopilot and the waypoint list is empty, force updateTimer = 0f so
the next IdleManager.Update tick calls FindActivity immediately.
Removes the 0–12s idle wait between drop-out and the next autonomous
action. Also covers jump-gate transitions where ETA math is unavailable.

Gated by [Autopilot] ArrivalSnap config entry."
```

---

## Task 3: ETA-sync patch — align the cycle timer with live travel ETA

**Goal of this task:** While the ship is warping between POIs in-system, continuously overwrite `updateTimer`/`updateTimerBase` so the green progress circle visibly fills in lockstep with arrival. Re-purposes ECHO's timer as a travel-ETA indicator and eliminates the no-op "cycle completes, calls FindActivity, bails because TravelActive, resets to 12s" spin that happens during long trips.

**Files:**
- Modify: `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs`

- [ ] **Step 1: Add the pure ETA-calculation helper**

At the bottom of the `AutopilotTimingPatches` class, add this pure helper (useful for clarity and future testability):

```csharp
    /// <summary>
    /// Compute estimated seconds-to-arrival from a remaining-distance and a
    /// current speed. Floors speed to a small epsilon so we never divide by
    /// zero or return a negative ETA when the ship has stopped momentarily
    /// (e.g. waiting on scene load).
    /// </summary>
    internal static float ComputeEtaSeconds(float remainingDistance, float travelSpeed)
    {
        const float minSpeed = 0.1f;
        float speed = Mathf.Max(travelSpeed, minSpeed);
        return Mathf.Max(0f, remainingDistance) / speed;
    }
```

- [ ] **Step 2: Add state tracking for the warping→non-warping transition**

Still inside the class, add a static field and a constant:

```csharp
    // Tracks whether our previous Update tick saw isWarping=true. Used so we
    // can capture the initial updateTimerBase at warp start and allow the
    // vanilla IdleManager cycle to resume naturally after warp ends.
    private static bool _wasSyncing;

    // Floor for updateTimerBase while ETA-syncing. If initial ETA is smaller
    // (e.g. very short hop), we clamp up so the fill circle always shows some
    // travel progress rather than a flash.
    private const float MinEtaBase = 3f;
```

- [ ] **Step 3: Add the IdleManager.Update postfix**

Still inside the class, add:

```csharp
    /// <summary>
    /// Postfix on <see cref="IdleManager.Update"/>. Runs every frame. When the
    /// player is on autopilot and <see cref="TravelManager.isWarping"/> is
    /// true, overwrite <c>updateTimer</c> with the live ETA so the progress
    /// circle becomes a travel-ETA indicator. When the game re-sets the timer
    /// via <c>FindActivity</c>'s no-op-during-travel branch, our postfix
    /// overwrites the 12s default back to the live ETA immediately.
    ///
    /// <c>updateTimerBase</c> is captured once at warp start and held steady,
    /// so <c>SideTabAutopilot</c>'s <c>fillAmount = 1 - updateTimer/base</c>
    /// formula produces a smooth 0→1 fill over the trip.
    /// </summary>
    [HarmonyPostfix]
    [HarmonyPatch(typeof(IdleManager), "Update")]
    private static void IdleManager_Update_Postfix(IdleManager __instance)
    {
        if (!Plugin.Instance.CfgAutopilotTiming.Value) return;
        if (!Plugin.Instance.CfgAutopilotEtaSync.Value)
        {
            _wasSyncing = false;
            return;
        }

        var player = GamePlayer.current;
        if (player == null || !player.autoPlay)
        {
            _wasSyncing = false;
            return;
        }

        var travel = Singleton<TravelManager>.Instance;
        if (travel == null || !travel.isWarping)
        {
            // Travel ended or was cancelled. Let the vanilla cycle resume:
            // the next FindActivity call (or the arrival-snap patch) will
            // restore a sane updateTimer/base pairing.
            _wasSyncing = false;
            return;
        }

        float eta = ComputeEtaSeconds(travel.remainingDistance, GetSpaceShipTravelSpeed());

        if (!_wasSyncing)
        {
            // First tick of a new warp — seed the base so the circle starts empty.
            float seededBase = Mathf.Max(eta, MinEtaBase);
            UpdateTimerBaseRef(__instance) = seededBase;
            Plugin.Log.LogDebug(
                $"[autopilot-timing] eta-sync begin: eta={eta:F2}s, base={seededBase:F2}s");
            _wasSyncing = true;
        }

        // Hold the base steady unless the trip lengthened (e.g. waypoint added
        // mid-flight). Only grow, never shrink — shrinking would make fillAmount
        // jump backward visually.
        float currentBase = UpdateTimerBaseRef(__instance);
        if (eta > currentBase)
        {
            UpdateTimerBaseRef(__instance) = eta;
        }

        // Always overwrite updateTimer with the live ETA. This replaces both
        // the vanilla `updateTimer -= Time.deltaTime` from IdleManager.Update
        // and any mid-travel FindActivity re-set.
        UpdateTimerRef(__instance) = eta;
    }

    /// <summary>
    /// Pull the current ship's warp speed off the singleton gameplay manager.
    /// Returns 0 (caller will floor) if the manager or ship is unavailable —
    /// which happens briefly during scene transitions and the first frame
    /// after emergency jumps.
    /// </summary>
    private static float GetSpaceShipTravelSpeed()
    {
        var gm = GameplayManager.Instance;
        if (gm == null) return 0f;
        var ship = gm.spaceShip;
        if (ship == null || ship.unitData == null) return 0f;
        return ship.unitData.travelSpeed;
    }
```

No new `using` line is needed — `GameplayManager` is declared in the global namespace (root of `Assembly-CSharp.dll`), so it's reachable without import. The using block at the top of `AutopilotTimingPatches.cs` should remain:

```csharp
using Behaviour.Gameplay;
using Behaviour.Managers;
using Behaviour.Util;
using HarmonyLib;
using Source.Player;
using UnityEngine;
```

- [ ] **Step 4: Build**

```bash
cd /home/fank/repo/vanguard-galaxy && make build
```

Expected: build succeeds with no errors. `GameplayManager` resolves because it lives in the global namespace of `Assembly-CSharp.dll` — no `using` is needed.

- [ ] **Step 5: Deploy**

```bash
cd /home/fank/repo/vanguard-galaxy && make deploy
```

- [ ] **Step 6: In-game verification — ETA sync**

1. Launch the game. Load a save.
2. Open the BepInEx console.
3. Press **T** to enable autopilot. Wait for the autopilot to initiate a warp to a POI at least 30 seconds away (mining, salvage, or cross-system travel; a nearby POI won't give you enough time to observe the effect).
4. The moment warp begins, expect one console line:

    ```
    [Debug  :Vanguard Galaxy TTS] [autopilot-timing] eta-sync begin: eta=NN.NNs, base=NN.NNs
    ```

    where NN.NN is the initial ETA in seconds.
5. Watch the green progress circle on the Autopilot side-tab. Expected behavior: starts empty at warp begin, fills smoothly over the entire trip, arrives at 100% at the exact moment the ship drops out of warp.
6. Compare to vanilla: with `EtaSync = false`, the circle would cycle 0→100% every 12 seconds during the trip regardless of distance. With the patch, there's one continuous fill covering the whole journey.
7. Combined with the arrival-snap patch from Task 2: the circle should visibly complete at drop-out AND the next activity should fire within one frame of reaching 100%.

- [ ] **Step 7: In-game verification — jump-gate case**

1. Trigger a multi-system journey (destination in a different system than the current one, so the autopilot will use a jump-gate).
2. Expect: `eta-sync begin` log fires for the in-system leg to the jumpgate. During the jumpgate cutscene (~4–5s of `WaitForSeconds`), `isWarping` is false, so the ETA-sync patch is inactive — the circle behaves vanilla. On the far side of the gate, the next in-system leg re-engages ETA-sync. When the final leg ends, arrival-snap fires.
3. Verify no error spam in the log during jump-gate transitions. If you see `[autopilot-timing] eta-sync begin` firing every frame, the `_wasSyncing` state is not being held correctly — re-check Step 3's implementation.

- [ ] **Step 8: Commit**

```bash
git add VGTTS/Patches/AutopilotTimingPatches.cs
git commit -m "feat: autopilot ETA-sync — map IdleManager cycle to live travel ETA

Postfix on IdleManager.Update: while TravelManager.isWarping is true and
the player is on autopilot, overwrite updateTimer with the live ETA
(remainingDistance / travelSpeed) and hold updateTimerBase at the
initial ETA of the leg. The SideTabAutopilot fill circle becomes a
smooth travel-progress indicator that completes exactly on drop-out.

Also kills the no-op FindActivity spin during long warps — instead of
the cycle resetting to 12s and calling FindActivity only to bail on
TravelActive(), our postfix re-overwrites with the ETA every tick.

Gated by [Autopilot] EtaSync config entry. Jump-gate transitions fall
back to the vanilla cycle (isWarping = false during the cutscene);
arrival-snap covers the post-gate drop-out."
```

---

## Task 4: Polish — log-level discipline and README note

**Goal of this task:** Downgrade the per-warp `eta-sync begin` log from `LogDebug` to `LogInfo` so it surfaces in the default BepInEx log-level without needing Debug enabled; add a short README note so future readers know about the [Autopilot] config section.

**Files:**
- Modify: `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs`
- Modify: `/home/fank/repo/vanguard-galaxy/README.md`

- [ ] **Step 1: Keep the per-warp log at `LogInfo`, leave per-frame at `LogDebug`**

In `/home/fank/repo/vanguard-galaxy/VGTTS/Patches/AutopilotTimingPatches.cs`, find:

```csharp
            Plugin.Log.LogDebug(
                $"[autopilot-timing] eta-sync begin: eta={eta:F2}s, base={seededBase:F2}s");
```

Change to `LogInfo` — this fires only once per warp (state-transition gated), so it's not spammy:

```csharp
            Plugin.Log.LogInfo(
                $"[autopilot-timing] eta-sync begin: eta={eta:F2}s, base={seededBase:F2}s");
```

Leave the `arrival-snap: zeroing updateTimer` line at `LogDebug` — that fires once per journey end, but we already have the `eta-sync begin` info line as a bookend so the debug level is appropriate for arrival.

- [ ] **Step 2: Append Autopilot section to README.md**

Open `/home/fank/repo/vanguard-galaxy/README.md`. After the existing `## Architecture (planned)` section (currently the last section in the file, ending near line 66), append a new section:

```markdown

## Autopilot timing tweaks

Separate from TTS: two Harmony patches that align the in-game autopilot
(IdleManager) task cycle with space-travel arrival. Both are disabled by
setting `[Autopilot] TimingEnabled = false` in `BepInEx/config/dev.fankserver.vgtts.cfg`.

- `[Autopilot] EtaSync` — while warping, the green progress circle on the
  Autopilot side-tab fills at the live travel ETA instead of the vanilla 12s
  loop. Circle completes exactly on drop-out.
- `[Autopilot] ArrivalSnap` — when the ship reaches its final waypoint, the
  IdleManager cycle timer is zeroed so the next autonomous action fires on
  the following frame instead of waiting up to 12s. Covers jump-gate
  transitions where ETA math is unavailable.

Neither patch changes what the autopilot decides to do; only *when* it
decides. Disable either independently via config.
```

- [ ] **Step 3: Build, deploy, verify once more**

```bash
cd /home/fank/repo/vanguard-galaxy && make deploy
```

Launch the game, engage autopilot, and confirm the `eta-sync begin` log now shows at the default BepInEx log level (no `LogLevels=Debug` override needed):

```
[Info   :Vanguard Galaxy TTS] [autopilot-timing] eta-sync begin: eta=42.18s, base=42.18s
```

- [ ] **Step 4: Commit**

```bash
git add VGTTS/Patches/AutopilotTimingPatches.cs README.md
git commit -m "docs: surface autopilot timing toggles in README + promote warp-begin log

Per-warp 'eta-sync begin' moves from LogDebug to LogInfo (fires once
per travel leg, so safe at info level). Arrival-snap log stays at
LogDebug. README gains an Autopilot section covering the two new
config toggles."
```

---

## Rollback notes

If any of the three features misbehave in a specific scenario:

- **Disable one feature:** edit `BepInEx/config/dev.fankserver.vgtts.cfg`, set the individual toggle to `false`, relaunch. No rebuild needed.
- **Disable all:** set `[Autopilot] TimingEnabled = false`.
- **Full revert:** `git revert` the Task 2, Task 3, and Task 4 commits. Task 1's scaffold can stay in place (empty class + dormant config entries) or be reverted with the fourth revert.

## Known limitations

1. **Jump-gate ETA is not synced.** `usingJumpgate` state has no exposed numeric ETA — it's driven by hardcoded `WaitForSeconds` calls in `TravelManager.JumpToSystem`. During the gate cutscene the circle reverts to vanilla behavior. The arrival-snap patch handles the post-gate state.
2. **ETA drifts under acceleration/deceleration.** `remainingDistance / travelSpeed` assumes constant speed, but the ship accelerates at warp start and decelerates near the destination. Expect the reported ETA to be slightly optimistic at warp start (overestimates time) and pessimistic near drop-out (underestimates). Drift is typically within 10%. Arrival-snap is the ultimate safety net — whatever the ETA predicted, the cycle zeroes on actual arrival.
3. **Fast-lane travel (7× multiplier) may cause ETA oscillation.** When `fastLaneTravelActive` flips between jumpgates, `travelSpeed` jumps. The ETA recomputes correctly but the `updateTimerBase` grow-only rule means the circle may pause visually while the base catches up. Acceptable for the uncommon case.
4. **Reflection targets C# compiler backing-field names.** If the game is recompiled with different IL output (e.g. ngen/IL2CPP — currently Mono, so not a concern), the `<updateTimer>k__BackingField` name could change. The plugin will log a Harmony exception at startup in that case; recover by updating the two `FieldRefAccess` string literals.

## Out of scope

These were discussed and deliberately deferred:

- Shortening `updateTimerBase` directly (12s → 6s) for a faster vanilla cycle. Orthogonal to arrival sync and can be layered later as a third toggle.
- Shortening `DelayIdleActivities(delay = 15f)` post-interaction cooldown. The `delayTimer` auto-clears in space anyway (`IdleManager.Update:94–96`), so its real-world impact is minimal; revisit only if needed.
- Filling in the unused `ExpertActivityDelay = 6f` constant as a fourth skill tier. That's a game-design change, not a timing alignment.
- Renaming the plugin from "VGTTS" to something broader. The `[Autopilot]` config section is the only user-visible signal that the plugin now does more than TTS; the plugin GUID/name change is a future deliverable.
