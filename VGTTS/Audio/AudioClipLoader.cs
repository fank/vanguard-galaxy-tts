using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

namespace VGTTS.Audio;

internal static class AudioClipLoader
{
    /// <summary>
    /// Load a WAV file into an <see cref="AudioClip"/>. Runs as a coroutine because
    /// UnityWebRequest is inherently async-per-frame. Invokes <paramref name="onDone"/>
    /// with the clip or null on failure.
    /// </summary>
    public static IEnumerator LoadWav(string path, Action<AudioClip?> onDone)
    {
        var url = "file:///" + path.Replace('\\', '/');
        using var req = UnityWebRequestMultimedia.GetAudioClip(url, AudioType.WAV);
        yield return req.SendWebRequest();

        if (req.result != UnityWebRequest.Result.Success)
        {
            Plugin.Log.LogWarning($"AudioClip load failed: {req.error} (path={path})");
            onDone(null);
            yield break;
        }

        var clip = DownloadHandlerAudioClip.GetContent(req);
        onDone(clip);
    }
}
