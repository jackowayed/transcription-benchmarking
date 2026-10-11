# Podcast transcription benchmarking

Measure alternatives to timestamped Faster Whisper `base.en`, CPU/int8, beam 3,
batch 4, two threads, VAD on, word alignment off. The use case is Gemini ad-region
detection: missing sponsor speech is more serious than isolated incorrect words.
Earlier experiments supplied by the user excluded tiny, blind beam-1 adoption,
and coarse timestamp-free batching. Those findings inform this benchmark; they
are not new measurements from this repository.

Run **Podcast transcription benchmark** from Actions. The workflow freezes one
recent full-length episode each of Served with Andy Roddick and The 404 Media
Podcast, then saves opening, three interior, and ending WAV samples. Every engine
receives exactly the same hashed audio. Dynamic ads can change on a new download;
never reuse acoustic labels against a different source hash.

The public repository's Linux runner is restricted to two logical CPUs using
`os.sched_setaffinity`, inherited by child processes. This limits compute but does
not reproduce a private repository's runner CPU generation, topology, or RAM.
Record and inspect `environment.json` before transferring speed conclusions.
For the actual paid two-vCPU machine, run this workflow in the production private
repository or make an authorized private copy. No visibility change is automatic.

Nine configurations compare batch 4/8/16, one/two threads, explicit English,
whisper.cpp base F16/Q5, and Parakeet 110M/v3 INT8 through sherpa-onnx. The baseline
explicitly sets `without_timestamps=False`; Faster Whisper's default batched
coarse chunks would change the downstream ad-boundary problem.

The first screening trial covers every configuration. Subsequent repetitions
retain candidates within 25% of the baseline transcription time and shuffle them
deterministically, keeping the experiment bounded. Report each repeat count. Each condition starts
in a fresh process on the same runner. Model loading is separate; Python models
are reused across clips in a trial. whisper.cpp receives all clips in one CLI
invocation and loads once; its reported load time is subtracted from process
wall time. Downloads and compilation occur before timing. Packages are pinned;
model revisions and hashes are captured in metadata. Parakeet processes every
sample in 25-second cores with one-second overlap context; tokens are retained
by core timestamp and grouped into at-most-eight-second segments. Its timestamps
and context behavior differ from Whisper and require downstream evaluation.

Small reports and transcripts are committed to the `benchmark-results` branch
under `runs/RUN_ID`, with incremental evidence after each completed trial. Audio
WAVs and native output are retained in Actions artifacts for 30 days. The report
includes real-time factor, load time, memory, and baseline disagreement. **Baseline
word deletions and timing gaps are review flags, not measured accuracy.**

A production recommendation needs full-episode checks on the actual private
runner and the existing Gemini classifier/edit planner, including repeated calls,
exact-audio labels or direct inspection of changed cuts, sponsor-block recall,
ad retention, and editorial loss. The current GitHub token does not provide a
Gemini credential or access to the production repository.

Local commands after installing Python requirements, FFmpeg, and building
whisper.cpp v1.9.5 under `whisper.cpp/`:

```bash
python scripts/corpus.py
python scripts/setup_models.py
REPEATS=2 python scripts/benchmark.py
python scripts/report.py
```

For Python integration, Faster Whisper and sherpa-onnx are direct APIs.
whisper.cpp can be invoked through `subprocess.run` and its JSON parsed into
`{start, end, text}` segments, as demonstrated in `scripts/trial.py`.
