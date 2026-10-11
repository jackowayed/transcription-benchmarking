"""One fresh-process trial. All backends emit clip-relative timed text."""
import argparse,json,pathlib,time,os,resource,subprocess,re,wave
import numpy as np

def read_audio(path):
 from faster_whisper.audio import decode_audio
 return decode_audio(path,sampling_rate=16000)

def parakeet_segments(recognizer,audio,token_sink=None):
 # Decode all samples in 25 s cores with 2 s context on either side.
 # Assign complete words to cores by their first token timestamp. This avoids
 # splitting a multi-piece word across independently decoded overlap windows.
 segments=[];length=len(audio)/16000
 for core in np.arange(0,length,25):
  lo=max(0,float(core)-2);hi=min(length,float(core)+27)
  stream=recognizer.create_stream();stream.accept_waveform(16000,audio[int(lo*16000):int(hi*16000)]);recognizer.decode_stream(stream)
  result=stream.result;tokens=list(result.tokens);times=list(result.timestamps);durations=list(getattr(result,'durations',[]))
  if result.text.strip() and not times:raise RuntimeError('Parakeet produced text without token timestamps')
  words=[]
  for i,(token,ts) in enumerate(zip(tokens,times)):
   t=lo+float(ts);dur=float(durations[i]) if i<len(durations) else (float(times[i+1]-ts) if i+1<len(times) else .1)
   end=min(length,t+max(.01,dur));text=token.replace('▁',' ')
   if token_sink is not None:token_sink.append({'core':float(core),'start':t,'end':end,'token':token})
   if not words or token.startswith(('▁',' ')):words.append({'start':t,'end':end,'text':text})
   else:words[-1]['text']+=text;words[-1]['end']=end
  group=[];start=last=end=None
  for word in words:
   t=word['start']
   if t<float(core) or t>=min(length,float(core)+25):continue
   if group and (t-last>.8 or t-start>=5):
    segments.append({'start':start,'end':end,'text':''.join(group).strip()});group=[]
   if not group:start=t
   group.append(word['text']);last=word['end'];end=word['end']
   if word['text'].rstrip().endswith(('.','?','!')):
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
   else:
    raw_tokens=[];segments=parakeet_segments(model,read_audio(clip['path']),raw_tokens)
   elapsed=time.perf_counter()-t;total+=elapsed
   entry={'id':clip['id'],'seconds':elapsed,'segments':segments}
   if backend=='sherpa-onnx':entry['native_tokens']=raw_tokens
   meta['clips'].append(entry)
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
