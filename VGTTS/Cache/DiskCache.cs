using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using BepInEx;

namespace VGTTS.Cache;

internal sealed class DiskCache
{
    private readonly string _cacheDir;

    public DiskCache(string subdir = "VGTTS")
    {
        _cacheDir = Path.Combine(Paths.CachePath, subdir);
        Directory.CreateDirectory(_cacheDir);
    }

    public string PathFor(string text, string voice)
    {
        var input = (voice ?? "") + "::" + (text ?? "");
        using var sha = SHA256.Create();
        var hash = sha.ComputeHash(Encoding.UTF8.GetBytes(input));
        return Path.Combine(_cacheDir, ToHex(hash) + ".wav");
    }

    public bool Exists(string path) => File.Exists(path) && new FileInfo(path).Length > 0;

    private static string ToHex(byte[] bytes)
    {
        var sb = new StringBuilder(bytes.Length * 2);
        foreach (var b in bytes) sb.Append(b.ToString("x2"));
        return sb.ToString();
    }
}
