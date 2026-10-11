"""Summarize timing and baseline disagreements, never label them accuracy."""
import pathlib,json,statistics,re,hashlib,sys
from jiwer import process_words

def normalized(text):return ' '.join(re.findall(r"[a-z0-9]+(?:'[a-z]+)?",text.lower()))
def digest(clips):return hashlib.sha256(json.dumps([{'id':c['id'],'segments':c['segments']} for c in clips],sort_keys=True).encode()).hexdigest()
def subtract(intervals,coverage):
 out=[]
 for a,b in intervals:
  pieces=[(a,b)]
  for c,d in coverage:
   nextpieces=[]
   for x,y in pieces:
    if d<=x or c>=y:nextpieces.append((x,y))
    else:
     if c>x:nextpieces.append((x,min(c,y)))
     if d<y:nextpieces.append((max(d,x),y))
   pieces=nextpieces
  out.extend(pieces)
 return out

def report(directory='outputs'):
 root=pathlib.Path(directory);environment=json.loads((root/'environment.json').read_text());configs=json.loads(pathlib.Path('configs.json').read_text());byid={}
 for c in configs:
  trials=[json.loads(p.read_text()) for p in sorted(root.glob(c['id']+'-r*.json'))];byid[c['id']]=trials
 baseline=byid.get('fw-baseline',[]);baseline_hashes={digest(t['clips']) for t in baseline};base={x['id']:x for x in baseline[0]['clips']} if baseline else {}
 manifest={x['id']:x for x in environment['corpus']['clips']};rows=[];review=[]
 for c in configs:
  trials=byid[c['id']]
  if not trials:continue
  timed=[x['transcribe_seconds'] for x in trials];texts=[' '.join(s['text'] for clip in x['clips'] for s in clip['segments']) for x in trials]
  row={'id':c['id'],'repeats':len(trials),'median_seconds':statistics.median(timed),'min_seconds':min(timed),'max_seconds':max(timed),'rtf':statistics.median([x['rtf'] for x in trials]),'seconds_per_audio_hour':statistics.median([x['rtf'] for x in trials])*3600,'median_load_seconds':statistics.median([x['model_load_seconds'] for x in trials]),'peak_rss_mb':max(x['peak_rss_mb'] for x in trials),'transcripts_identical_across_repeats':len({digest(x['clips']) for x in trials})==1,'words':len(normalized(texts[0]).split()),'matches_observed_baseline_transcripts':bool(baseline_hashes) and all(digest(t['clips']) in baseline_hashes for t in trials)}
  # Timestamp gaps and reference deletions identify passages to review.
  # These compare model output with baseline; neither is ground truth.
  disagreements=[];deletions=refwords=0
  for clip in trials[0]['clips']:
   if clip['id'] not in base:continue
   control=base[clip['id']];ref=normalized(' '.join(s['text'] for s in control['segments']));hyp=normalized(' '.join(s['text'] for s in clip['segments']))
   compare=process_words(ref,hyp);deletions+=compare.deletions;refwords+=len(ref.split())
   missing=subtract([(s['start'],s['end']) for s in control['segments'] if s['text'].strip()],[(s['start'],s['end']) for s in clip['segments'] if s['text'].strip()])
   for start,end in missing:
    if end-start<5:continue
    source=manifest[clip['id']]
    texts=[s['text'] for s in control['segments'] if s['start']<end and s['end']>start]
    disagreements.append({'clip':clip['id'],'start':start,'end':end,'episode_start':source['offset']+start,'episode_end':source['offset']+end,'baseline_text':' '.join(texts)})
   review.append({'config':c['id'],'clip':clip['id'],'baseline_deletion_fraction':compare.deletions/max(1,len(ref.split())),'baseline':ref,'candidate':hyp})
  row['baseline_word_deletion_fraction']=deletions/max(1,refwords);row['baseline_timing_gaps_ge_5s']=disagreements;rows.append(row)
 (root/'summary.json').write_text(json.dumps(rows,indent=2));(root/'coverage-review.json').write_text(json.dumps(review,indent=2))
 total=sum(x['duration'] for x in manifest.values());lines=['# Measured transcription benchmark','',f'Audio: {total/60:.1f} minutes; two-CPU affinity on a public GitHub Actions runner.','', '| Configuration | Median seconds | Range | Seconds / audio hour | Load seconds | Baseline word deletions | >=5 s timing gaps | Exact baseline text/times |','|---|---:|---:|---:|---:|---:|---:|---|']
 for x in sorted(rows,key=lambda r:r['median_seconds']):lines.append(f"| {x['id']} | {x['median_seconds']:.2f} | {x['min_seconds']:.2f}–{x['max_seconds']:.2f} | {x['seconds_per_audio_hour']:.1f} | {x['median_load_seconds']:.2f} | {x['baseline_word_deletion_fraction']:.1%} | {len(x['baseline_timing_gaps_ge_5s'])} | {'yes' if x['matches_observed_baseline_transcripts'] else 'no'} |")
 lines+=['','Repeat counts and any failed trials are in summary.json and trials.json. Slow engines receive one screening trial; competitive conditions are repeated.', '', 'Timing includes decoding, VAD where enabled, and fully consumed transcription. Downloads and model load are separate. Native CLI transcription time subtracts the reported model load from wall time; CLI startup remains included.','', 'Word deletions and timing gaps measure disagreement with Faster Whisper baseline, not accuracy or missed ads. Parakeet uses overlapping fixed windows and token-derived segments, rather than Whisper VAD/timestamp tokens. Ad boundaries need audio-backed downstream validation.','', '## Frozen episodes','']
 for e in environment['corpus']['episodes']:lines.append(f"- {e['show']}: {e['title']} ({e['published']}); source SHA-256 `{e['source_sha256']}`")
 (root/'report.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':report(sys.argv[1] if len(sys.argv)>1 else 'outputs')
