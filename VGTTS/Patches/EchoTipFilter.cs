using System.Collections.Generic;
using Source.Player;
using Source.Simulation.Story;
using UnityEngine;

namespace VGTTS.Patches;

/// <summary>
/// Decides whether an ECHO HUD travel hint should get voiced.
/// Three independent gates, any one can veto:
///   • mode gate — InSandbox / InConquest config toggles
///   • duration gate — suppress during the first N seconds of a travel leg
///     (populated via <see cref="HudManagerPatches"/>)
///   • unseen-only gate — each hint plays voice at most once until the pool
///     refills, which is heuristically ~60 distinct tips
///
/// Visual hints are never suppressed — only the voice synthesis is skipped.
/// </summary>
internal static class EchoTipFilter
{
    private static readonly HashSet<string> _seenThisCycle = new();
    private static float _travelStartTime = -999f;

    /// <summary>Threshold for clearing the seen-set — the game pool maxes at
    /// 42 TravelTip + 23 Sandbox + 1 Conquest = 66 keys; once we've heard ~60
    /// of them we declare the cycle complete and restart.</summary>
    private const int SeenCycleResetThreshold = 60;

    /// <summary>Called by <see cref="HudManagerPatches"/> when a travel leg starts.</summary>
    public static void OnTravelStart()
    {
        _travelStartTime = Time.realtimeSinceStartup;
    }

    public static bool ShouldSpeak(string text)
    {
        var plugin = Plugin.Instance;
        if (plugin == null) return true;

        // 1. Mode gate
        var player = GamePlayer.current;
        if (player != null)
        {
            if (player.HasStoryteller<Sandbox>() && !plugin.CfgEchoTipsInSandbox.Value)
                return false;
            if (player.HasStoryteller<Conquest>() && !plugin.CfgEchoTipsInConquest.Value)
                return false;
        }

        // 2. Min-travel-duration gate
        var minSeconds = plugin.CfgEchoTipsMinTravelSeconds.Value;
        if (minSeconds > 0f)
        {
            var elapsed = Time.realtimeSinceStartup - _travelStartTime;
            if (elapsed < minSeconds) return false;
        }

        // 3. Unseen-only gate — HashSet.Add returns false if already present.
        if (plugin.CfgEchoTipsUnseenOnly.Value)
        {
            if (!_seenThisCycle.Add(text))
            {
                if (_seenThisCycle.Count >= SeenCycleResetThreshold)
                    _seenThisCycle.Clear();
                return false;
            }
        }

        return true;
    }
}
