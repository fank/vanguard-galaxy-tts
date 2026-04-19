using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using BepInEx;

namespace VGTTS.Cache;

/// <summary>
/// Two-tier disk cache for live-TTS output:
///   - <b>Persistent</b> (default): <c>&lt;BepInEx&gt;/cache/VGTTS/*.wav</c>
///     Used for named NPCs whose dialogue is bounded and reused across
///     sessions (captain-name lines, commander-rename recovery, etc.).
///   - <b>Session</b>: <c>&lt;BepInEx&gt;/cache/VGTTS/session/*.wav</c>
///     Used for procedurally-named speakers (distress rescue victims,
///     bar salesmen, crew recruits). Wiped on every plugin load so the
///     cache doesn't accumulate tens of MB of never-reused voice lines.
/// </summary>
internal sealed class DiskCache
{
    private readonly string _persistentDir;
    private readonly string _sessionDir;

    public DiskCache(string subdir = "VGTTS")
    {
        _persistentDir = Path.Combine(Paths.CachePath, subdir);
        _sessionDir = Path.Combine(_persistentDir, "session");
        Directory.CreateDirectory(_persistentDir);
        Directory.CreateDirectory(_sessionDir);
        PurgeSession();
    }

    /// <summary>Return the cache path for (text, voice). <paramref name="persistent"/>
    /// = true for known NPCs (kept across sessions), false for procedural
    /// speakers (wiped at next launch).</summary>
    public string PathFor(string text, string voice, bool persistent = true)
    {
        var input = (voice ?? "") + "::" + (text ?? "");
        using var sha = SHA256.Create();
        var hash = sha.ComputeHash(Encoding.UTF8.GetBytes(input));
        var dir = persistent ? _persistentDir : _sessionDir;
        return Path.Combine(dir, ToHex(hash) + ".wav");
    }

    public bool Exists(string path) => File.Exists(path) && new FileInfo(path).Length > 0;

    /// <summary>Delete all WAVs under the session subdir. Called once at startup
    /// so procedural NPC audio from previous launches doesn't linger.</summary>
    private void PurgeSession()
    {
        try
        {
            var deleted = 0;
            foreach (var f in Directory.GetFiles(_sessionDir, "*.wav"))
            {
                try { File.Delete(f); deleted++; } catch { /* best-effort */ }
            }
            if (deleted > 0)
                Plugin.Log.LogInfo($"[cache] Purged {deleted} session WAVs from previous launch");
        }
        catch (Exception ex)
        {
            Plugin.Log.LogWarning($"[cache] Session purge failed: {ex.Message}");
        }
    }

    private static string ToHex(byte[] bytes)
    {
        var sb = new StringBuilder(bytes.Length * 2);
        foreach (var b in bytes) sb.Append(b.ToString("x2"));
        return sb.ToString();
    }
}
