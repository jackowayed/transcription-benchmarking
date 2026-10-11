# Measured transcription benchmark

Audio: 33.0 minutes; two-CPU affinity on a public GitHub Actions runner.

| Configuration | Median seconds | Range | Seconds / audio hour | Load seconds | Baseline word deletions | >=5 s timing gaps | Exact baseline text/times |
|---|---:|---:|---:|---:|---:|---:|---|
| parakeet-110m | 41.76 | 40.44–43.07 | 75.9 | 0.55 | 1.9% | 1 | no |
| fw-batch16 | 51.94 | 51.93–51.96 | 94.4 | 0.23 | 0.0% | 0 | yes |
| fw-baseline | 56.29 | 53.57–59.01 | 102.3 | 0.24 | 0.0% | 0 | yes |
| fw-batch8 | 56.34 | 54.27–58.41 | 102.4 | 0.25 | 0.0% | 0 | yes |
| fw-english | 56.67 | 54.14–59.19 | 103.0 | 0.24 | 0.0% | 0 | yes |
| fw-thread1 | 60.89 | 60.83–60.94 | 110.7 | 0.23 | 0.0% | 0 | yes |
| parakeet-v3 | 140.11 | 140.11–140.11 | 254.7 | 1.17 | 1.5% | 2 | no |
| cpp-base-f16 | 255.44 | 255.44–255.44 | 464.4 | 0.03 | 2.0% | 1 | no |
| cpp-base-q5 | 285.97 | 285.97–285.97 | 519.9 | 0.02 | 1.6% | 2 | no |

Repeat counts and any failed trials are in summary.json and trials.json. Slow engines receive one screening trial; competitive conditions are repeated.

Timing includes decoding, VAD where enabled, and fully consumed transcription. Downloads and model load are separate. Native CLI transcription time subtracts the reported model load from wall time; CLI startup remains included.

Word deletions and timing gaps measure disagreement with Faster Whisper baseline, not accuracy or missed ads. Parakeet uses overlapping fixed windows and token-derived segments, rather than Whisper VAD/timestamp tokens. Ad boundaries need audio-backed downstream validation.

## Frozen episodes

- served: Should Grand Slam Runner-Ups Have to Speak? Andy Roddick on Ben Shelton & Wimbledon 2009 | Q&Andy (Thu, 08 Oct 2026 03:00:00 -0000); source SHA-256 `1e5287773431cb18f4ce186023b5fb56237350e8240378ffb686a53304d68c95`
- 404media: The Social Reckoning’s Real-Life Whistleblower (Fri, 09 Oct 2026 15:45:00 -0000); source SHA-256 `5ab0bf61421cfa2093919ab97364f6a1025e8b6e5bc7e3e2936155251268f501`
