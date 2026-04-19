using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;

namespace VGTTS.TTS;

/// <summary>
/// Offline neural TTS via Kokoro v1.0, dispatched through sherpa-onnx's
/// standalone Windows binary. Voice strings use the <c>kokoro:SID</c> convention
/// (e.g. <c>kokoro:23</c>); malformed input falls back to the plugin default.
///
/// Expected bundle layout (relative to the plugin DLL):
/// <code>
///   tools/sherpa/sherpa-onnx-tts.exe
///   tools/kokoro/model.onnx
///   tools/kokoro/voices.bin
///   tools/kokoro/tokens.txt
///   tools/kokoro/lexicon-us-en.txt
///   tools/kokoro/espeak-ng-data/
/// </code>
/// </summary>
internal sealed class KokoroProvider
{
    private const string Prefix = "kokoro:";
    private const int DefaultSpeaker = 0;

    private readonly string _sherpaExe;
    private readonly string _kokoroDir;

    public KokoroProvider()
    {
        var pluginDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        var bundle = Path.Combine(pluginDir, "tools");
        _sherpaExe = Path.Combine(bundle, "sherpa", "sherpa-onnx-tts.exe");
        _kokoroDir = Path.Combine(bundle, "kokoro");

        if (!File.Exists(_sherpaExe))
            throw new FileNotFoundException($"sherpa-onnx-tts.exe not found at {_sherpaExe}");
        if (!File.Exists(Path.Combine(_kokoroDir, "model.onnx")))
            throw new FileNotFoundException($"Kokoro model.onnx not found under {_kokoroDir}");
    }

    public Task<string> SynthesizeAsync(string text, string voice, string outputPath, CancellationToken ct)
    {
        return Task.Run(() =>
        {
            var speaker = ParseSpeaker(voice) ?? DefaultSpeaker;
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath)!);

            var modelPath   = Path.Combine(_kokoroDir, "model.onnx");
            var voicesPath  = Path.Combine(_kokoroDir, "voices.bin");
            var tokensPath  = Path.Combine(_kokoroDir, "tokens.txt");
            var dataDir     = Path.Combine(_kokoroDir, "espeak-ng-data");
            var lexiconPath = Path.Combine(_kokoroDir, "lexicon-us-en.txt");

            // Quoting everything because Steam's install path contains spaces.
            var args =
                $"--kokoro-model=\"{modelPath}\" " +
                $"--kokoro-voices=\"{voicesPath}\" " +
                $"--kokoro-tokens=\"{tokensPath}\" " +
                $"--kokoro-data-dir=\"{dataDir}\" " +
                $"--kokoro-lexicon=\"{lexiconPath}\" " +
                $"--num-threads=2 " +
                $"--sid={speaker} " +
                $"--output-filename=\"{outputPath}\" " +
                $"\"{text.Replace("\"", "\\\"")}\"";

            var psi = new ProcessStartInfo(_sherpaExe)
            {
                Arguments = args,
                WorkingDirectory = Path.GetDirectoryName(_sherpaExe),
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardError = true,
                RedirectStandardOutput = true,
            };

            using var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Failed to start sherpa-onnx-tts.exe");
            using var ctReg = ct.Register(() => { try { proc.Kill(); } catch { } });

            var stderr = proc.StandardError.ReadToEnd();
            proc.WaitForExit();

            if (proc.ExitCode != 0 || !File.Exists(outputPath) || new FileInfo(outputPath).Length == 0)
                throw new InvalidOperationException(
                    $"Kokoro synthesis failed (exit {proc.ExitCode}): {stderr.Trim()}");

            return outputPath;
        }, ct);
    }

    private static int? ParseSpeaker(string voice)
    {
        if (string.IsNullOrEmpty(voice)) return null;
        if (!voice.StartsWith(Prefix, StringComparison.OrdinalIgnoreCase)) return null;
        var rest = voice.Substring(Prefix.Length);
        return int.TryParse(rest, out var sid) ? sid : null;
    }
}
