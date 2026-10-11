# Measured transcription benchmark

Audio: 33.0 minutes; two-CPU affinity on a public GitHub Actions runner.

| Configuration | Median seconds | Range | Seconds / audio hour | Load seconds | Baseline word deletions | >=5 s timing gaps | Exact baseline text/times |
|---|---:|---:|---:|---:|---:|---:|---|
| parakeet-110m | 45.64 | 44.62–46.67 | 83.0 | 0.56 | 1.9% | 0 | no |
| fw-baseline | 57.88 | 57.08–58.67 | 105.2 | 0.25 | 0.0% | 0 | yes |

Repeat counts and any failed trials are in summary.json and trials.json. Slow engines receive one screening trial; competitive conditions are repeated.

Timing includes decoding, VAD where enabled, and fully consumed transcription. Downloads and model load are separate. Native CLI transcription time subtracts the reported model load from wall time; CLI startup remains included.

Word deletions and timing gaps measure disagreement with Faster Whisper baseline, not accuracy or missed ads. Parakeet uses overlapping fixed windows and token-derived segments, rather than Whisper VAD/timestamp tokens. Ad boundaries need audio-backed downstream validation.

## Frozen episodes

- served: Should Grand Slam Runner-Ups Have to Speak? Andy Roddick on Ben Shelton & Wimbledon 2009 | Q&Andy (Thu, 08 Oct 2026 03:00:00 -0000); source SHA-256 `1e5287773431cb18f4ce186023b5fb56237350e8240378ffb686a53304d68c95`
- 404media: The Social Reckoning’s Real-Life Whistleblower (Fri, 09 Oct 2026 15:45:00 -0000); source SHA-256 `5ab0bf61421cfa2093919ab97364f6a1025e8b6e5bc7e3e2936155251268f501`
