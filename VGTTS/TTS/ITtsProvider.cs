using System.Threading;
using System.Threading.Tasks;

namespace VGTTS.TTS;

/// <summary>
/// Back-end that synthesizes speech to a WAV file on disk. Implementations must be safe
/// to call from a background thread.
/// </summary>
internal interface ITtsProvider
{
    string Name { get; }

    /// <summary>
    /// Synthesize <paramref name="text"/> in <paramref name="voice"/> and write a WAV file
    /// to <paramref name="outputPath"/>. Returns the path when complete.
    /// </summary>
    Task<string> SynthesizeAsync(string text, string voice, string outputPath, CancellationToken ct);
}
