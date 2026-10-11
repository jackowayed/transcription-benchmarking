# Measured recommendation

Use timestamped Faster Whisper `base.en` CPU/INT8, beam 3, **batch size 16 and two threads**. On the two complete original MP3s (80.7 minutes total), this reduced median transcription time by **9.7%**. All 1,163 text/timestamp segments were identical across the baseline, batch-16, and one-thread trials, including both repetitions. No newly omitted transcript content was observed from this batch change.

This is a transcription-content comparison. The production adapter and Gemini classifier/edit planner were not available, and no Gemini calls or ground-truth ad-cut accuracy measurements were performed.

| Complete original MP3s, x86 | Repeats | Median transcription | Range | Peak process RSS |
|---|---:|---:|---:|---:|
| fw-baseline | 2 | 229.50 s | 227.44–231.57 s | 1170 MiB |
| fw-batch16 | 2 | 207.24 s | 206.95–207.52 s | 2029 MiB |
| fw-thread1 | 2 | 253.57 s | 252.99–254.15 s | 1188 MiB |

The Served episode improved by 9.1%; the 404 Media episode improved by 10.0%. Batch 16 used about 2 GiB at peak. One thread increased total transcription time by 10.5%. Model loading took about 0.3 seconds and was recorded separately. Source download, dependency installation, and model download were outside these transcription timings.

## Apply to Python

Change `batch_size` from 4 to 16 in the supplied configuration; keep the other settings. The compatible dataclass values are in [recommended-faster-whisper.json](recommended-faster-whisper.json). Explicit timestamp-token generation is essential:

```python
model = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=2)
pipeline = BatchedInferencePipeline(model=model)
segments, info = pipeline.transcribe(
    audio_path, beam_size=3, batch_size=16, vad_filter=True,
    word_timestamps=False, without_timestamps=False, language=None,
)
segments = list(segments)  # fully consume inference; reuse the model across files
```

Imports are `from faster_whisper import WhisperModel, BatchedInferencePipeline`. This benchmark used Faster Whisper 1.2.1 and CTranslate2 4.8.2. Default batched `without_timestamps=True` would change segment granularity and the ad-boundary problem.

## Faster model candidate

Parakeet 110M INT8 through sherpa-onnx used **21.1% less transcription time** in its corrected, paired 33-minute sample benchmark: 45.64 seconds versus 57.88 for Faster Whisper batch 4 (two repetitions each).

The corrected adapter decodes every sample in 25-second cores with two seconds of context on either side, assigns complete words to cores, and retains native token timings. Initial screening used one-second context and split token ownership; its faster 41.76-second median should not be used as the corrected adapter timing.

Opening/closing sponsor passages remain recognizable in text review. The corrected output had no five-second gaps against baseline segment coverage, but had 1.9% normalized reference-word deletions and different text/timestamps. Those are disagreement metrics, not accuracy, ad recall, or proof that no speech was lost. Whole-episode Parakeet and production Gemini cut validation remain outstanding; classifier/edit-planner code and a configured Gemini secret are needed. Keep it as an experimental backend rather than replacing the selected setting on speed alone.

The Parakeet model is `sherpa-onnx-nemo-parakeet_tdt_transducer_110m-en-36000-int8`. Its Python integration and overlap handling are demonstrated in [scripts/trial.py](scripts/trial.py). There is no shell requirement.

## Other screening results

| x86, same 33 minutes of frozen WAV samples | Median seconds | Repeats |
|---|---:|---:|
| fw-baseline | 56.29 | 2 |
| fw-batch8 | 56.34 | 2 |
| fw-batch16 | 51.94 | 2 |
| fw-thread1 | 60.89 | 2 |
| fw-english | 56.67 | 2 |
| cpp-base-q5 | 285.97 | 1 |
| cpp-base-f16 | 255.44 | 1 |
| parakeet-v3 | 140.11 | 1 |

Batch 8 and explicit English offered no useful median speed gain. The tested whisper.cpp F16/Q5_1 settings and Parakeet v3 were substantially slower. The slower engines received one screening trial; competitive configurations received two.

The standard `ubuntu-24.04-arm` check reused the exact same WAVs. Two ARM Neoverse-N2 cores took 175.13 seconds with batch 4 and 154.75 seconds with batch 16 (one screening trial each), roughly three times the x86 timings. ARM text/timestamps also differed from x86. This test gives no reason to switch to ARM for speed.

## Hardware and scope

The repository is public. These are public GitHub Actions runners with affinity restricted to two logical CPUs, **not measurements from a billed private-repository job**. On x86 the selected CPUs shared one physical AMD EPYC 9V74 core; on ARM they were two distinct cores. Affinity does not recreate a private runner’s entire CPU allocation, memory, host contention, or generation. Run this workflow in the production private repository before treating the absolute times as production timings.

A new podcast download can insert different ads: source MP3 hashes changed between screening and full validation. Conditions within each run share a frozen source; ARM and corrected Parakeet reused the exact screening audio. Never treat rates from the short WAV samples and whole original MP3s as interchangeable.

## Reproducible evidence

- x86-screen: [successful Actions run](https://github.com/jackowayed/transcription-benchmarking/actions/runs/38153523472), [immutable raw report/transcripts](https://github.com/jackowayed/transcription-benchmarking/tree/4736ad741009cf4b5d2b08595306703c94115040/runs/38153523472), [local summary](results/x86-screen/report.md), [environment](results/x86-screen/environment.json).
- full-mp3: [successful Actions run](https://github.com/jackowayed/transcription-benchmarking/actions/runs/38154275111), [immutable raw report/transcripts](https://github.com/jackowayed/transcription-benchmarking/tree/19619ee4412238013b984d591081df1561e7dde8/runs/38154275111), [local summary](results/full-mp3/report.md), [environment](results/full-mp3/environment.json).
- parakeet-corrected: [successful Actions run](https://github.com/jackowayed/transcription-benchmarking/actions/runs/38155690799), [immutable raw report/transcripts](https://github.com/jackowayed/transcription-benchmarking/tree/632b9d41b19b66c555d35805221f812d9f6e7693/runs/38155690799), [local summary](results/parakeet-corrected/report.md), [environment](results/parakeet-corrected/environment.json).
- arm-screen: [successful Actions run](https://github.com/jackowayed/transcription-benchmarking/actions/runs/38155694987), [immutable raw report/transcripts](https://github.com/jackowayed/transcription-benchmarking/tree/d4b04c8c9226457e747b5265cdc51195e5c4e167/runs/38155694987), [local summary](results/arm-screen/report.md), [environment](results/arm-screen/environment.json).

All four evidence runs succeeded: 27 timed configuration trials in total. Validation included fully consumed inference, exact full-episode segment hashes, source hashes across reused audio, overlap tests with boundary-spanning words, report aggregation/interval checks, Python syntax, and workflow YAML. Artifacts retain exact audio; raw text/metadata are also committed on result branches.
