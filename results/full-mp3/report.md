# Measured transcription benchmark

Audio: 80.7 minutes; two-CPU affinity on a public GitHub Actions runner.

| Configuration | Median seconds | Range | Seconds / audio hour | Load seconds | Baseline word deletions | >=5 s timing gaps | Exact baseline text/times |
|---|---:|---:|---:|---:|---:|---:|---|
| fw-batch16 | 207.24 | 206.95–207.52 | 154.1 | 0.33 | 0.0% | 0 | yes |
| fw-baseline | 229.50 | 227.44–231.57 | 170.7 | 0.34 | 0.0% | 0 | yes |
| fw-thread1 | 253.57 | 252.99–254.15 | 188.6 | 0.32 | 0.0% | 0 | yes |

Repeat counts and any failed trials are in summary.json and trials.json. Slow engines receive one screening trial; competitive conditions are repeated.

Timing includes decoding, VAD where enabled, and fully consumed transcription. Downloads and model load are separate. Native CLI transcription time subtracts the reported model load from wall time; CLI startup remains included.

Word deletions and timing gaps measure disagreement with Faster Whisper baseline, not accuracy or missed ads. Parakeet uses overlapping fixed windows and token-derived segments, rather than Whisper VAD/timestamp tokens. Ad boundaries need audio-backed downstream validation.

## Frozen episodes

- served: Should Grand Slam Runner-Ups Have to Speak? Andy Roddick on Ben Shelton & Wimbledon 2009 | Q&Andy (Thu, 08 Oct 2026 03:00:00 -0000); source SHA-256 `e85d4e024e7eeb208220b45eeec1a5cdb565fde04a118b59714649cdd56a1434`
- 404media: The Social Reckoning’s Real-Life Whistleblower (Fri, 09 Oct 2026 15:45:00 -0000); source SHA-256 `5f72969cc746fb10a513eb8be7e2325500d97daec3233bf9c5ca61fbfcee55dc`
