"""One fresh-process trial. All backends emit clip-relative timed text."""
import argparse,json,pathlib,time,os,resource,subprocess,re,wave
import numpy as np

def read_audio(path):
 with wave.open(path) as w:
  assert w.getframerate()==16000 and w.getnchannels()==1
  return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768

def parakeet_segments(recognizer,audio):
 # Decode every sample, with 1 s of context on either side of each 25 s core.
 # Retain tokens by core timestamp to avoid duplicating overlap text.
 segments=[];length=len(audio)/16000
 for core in np.arange(0,length,25):
  lo=max(0,float(core)-1);hi=min(length,float(core)+26)
  stream=recognizer.create_stream();stream.accept_waveform(16000,audio[int(lo*16000):int(hi*16000)]);recognizer.decode_stream(stream)
  result=stream.result;tokens=list(result.tokens);times=list(result.timestamps);durations=list(getattr(result,'durations',[]))
  if result.text.strip() and not times:
   raise RuntimeError('Parakeet produced text without token timestamps')
  group=[];start=last=end=None
  for i,(token,ts) in enumerate(zip(tokens,times)):
   t=lo+float(ts)
   if t<float(core) or t>=min(length,float(core)+25):continue
   dur=float(durations[i]) if i<len(durations) else (float(times[i+1]-ts) if i+1<len(times) else .1)
   text=token.replace('▁',' ')
   if group and (t-last>.8 or t-start>=8):
    segments.append({'start':start,'end':end,'text':''.join(group).strip()});group=[]
   if not group:start=t
   group.append(text);last=t;end=min(length,t+max(.01,dur))
   if text.rstrip().endswith(('.','?','!')):
    segments.append({'start':start,'end':end,'text':''.join(group).strip()});group=[]
  if group:segments.append({'start':start,'end':end,'text':''.join(group).strip()})
 return segments

def run(config,manifest,models):
 meta={'config':config,'affinity':sorted(os.sched_getaffinity(0)),'clips':[]};backend=config['backend'];modelpath=models[backend+':'+config['model']]['path']
 t=time.perf_counter()
 if backend=='faster-whisper':
  from faster_whisper import WhisperModel,BatchedInferencePipeline
  model=WhisperModel(modelpath,device='cpu',compute_type='int8',cpu_threads=config['threads'],num_workers=1)
  pipeline=BatchedInferencePipeline(model=model)
 elif backend=='sherpa-onnx':
  import sherpa_onnx
  directory=pathlib.Path(modelpath)
  def find(kind):
   paths=list(directory.glob(kind+'*.onnx'))
   return str(next((p for p in paths if 'int8' in p.name),paths[0]))
  model=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=find('encoder'),decoder=find('decoder'),joiner=find('joiner'),tokens=str(directory/'tokens.txt'),num_threads=config['threads'],model_type='nemo_transducer',decoding_method='greedy_search',provider='cpu')
 meta['model_load_seconds']=time.perf_counter()-t
 if backend=='whisper.cpp':
  # A single CLI invocation loads the model once and transcribes all files.
  outdir=pathlib.Path(os.environ['TRIAL_OUTPUT']);outdir.mkdir(parents=True,exist_ok=True)
  cmd=['whisper.cpp/build/bin/whisper-cli','-m',modelpath,'-t',str(config['threads']),'-bs',str(config['beam']),'-bo','3','-l','en','-ng','-oj','--vad','-vm',models['cpp_vad']['path'],'-vsd','2000','-vp','400']
  for clip in manifest['clips']:cmd+=['-f',clip['path'],'-of',str(outdir/clip['id'])]
  t=time.perf_counter();result=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=2400);elapsed=time.perf_counter()-t
  (outdir/'native.stderr.txt').write_text(result.stderr)
  if result.returncode:raise RuntimeError(result.stderr[-4000:])
  match=re.search(r'load time\s*=\s*([\d.]+) ms',result.stderr)
  load=float(match.group(1))/1000 if match else 0
  if not match:raise RuntimeError('Could not separate native model load timing')
  meta.update(model_load_seconds=load,process_seconds=elapsed,transcribe_seconds=elapsed-load,timing_note='CLI wall time minus reported model load; includes CLI startup and audio decoding; model loaded once')
  for clip in manifest['clips']:
   native=json.loads((outdir/(clip['id']+'.json')).read_text())
   segments=[{'start':x['offsets']['from']/1000,'end':x['offsets']['to']/1000,'text':x['text'].strip()} for x in native['transcription']]
   meta['clips'].append({'id':clip['id'],'segments':segments})
 else:
  total=0
  for clip in manifest['clips']:
   t=time.perf_counter()
   if backend=='faster-whisper':
    gen,info=pipeline.transcribe(clip['path'],beam_size=config['beam'],batch_size=config['batch'],vad_filter=True,word_timestamps=False,without_timestamps=False,language=config.get('language'))
    segments=[{'start':x.start,'end':x.end,'text':x.text.strip()} for x in gen]
   else:segments=parakeet_segments(model,read_audio(clip['path']))
   elapsed=time.perf_counter()-t;total+=elapsed
   meta['clips'].append({'id':clip['id'],'seconds':elapsed,'segments':segments})
  meta['transcribe_seconds']=total
 meta['audio_seconds']=sum(x['duration'] for x in manifest['clips']);meta['rtf']=meta['transcribe_seconds']/meta['audio_seconds'];meta['peak_rss_mb']=max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)/1024;meta['rss_measurement']='largest process peak RSS (parent or native child)'
 return meta

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
 config=json.loads(args.config);os.environ['TRIAL_OUTPUT']=str(pathlib.Path(args.output).with_suffix(''))
 try:
  result=run(config,json.loads(pathlib.Path('data/manifest.json').read_text()),json.loads(pathlib.Path('models/manifest.json').read_text()))
 except Exception:
  import traceback
  pathlib.Path(args.output).with_suffix('.error.txt').write_text(traceback.format_exc())
  raise
 pathlib.Path(args.output).write_text(json.dumps(result,indent=2));print(config['id'],result['transcribe_seconds'],result['rtf'],flush=True)
