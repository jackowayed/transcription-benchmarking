import json,pathlib,os,subprocess,sys,random,time,platform,importlib.metadata
root=pathlib.Path('outputs');root.mkdir(exist_ok=True)
allowed=sorted(os.sched_getaffinity(0));assert len(allowed)>=2;os.sched_setaffinity(0,allowed[:2])
from configuration import selected_configs
configs=selected_configs()
environment={'platform':platform.platform(),'cpu':subprocess.check_output(['lscpu'],text=True),'selected_cpus':allowed[:2],'cpu_topology':subprocess.check_output(['lscpu','-e=CPU,CORE,SOCKET,ONLINE'],text=True),'github_sha':os.environ.get('GITHUB_SHA'),'run_id':os.environ.get('GITHUB_RUN_ID'),'versions':{p:importlib.metadata.version(p) for p in ['faster-whisper','ctranslate2','sherpa-onnx','numpy','onnxruntime','jiwer']},'cpp_commit':subprocess.check_output(['git','-C','whisper.cpp','rev-parse','HEAD'],text=True).strip() if pathlib.Path('whisper.cpp/.git').exists() else None,'corpus':json.loads(pathlib.Path('data/manifest.json').read_text()),'models':json.loads(pathlib.Path('models/manifest.json').read_text())}
(root/'environment.json').write_text(json.dumps(environment,indent=2));trials=[]
for repeat in range(int(os.environ.get('REPEATS','2'))):
 order=configs.copy()
 if repeat>0:
  baseline=json.loads((root/'fw-baseline-r0.json').read_text())['transcribe_seconds']
  order=[c for c in configs if (root/(c['id']+'-r0.json')).exists() and json.loads((root/(c['id']+'-r0.json')).read_text())['transcribe_seconds']<=baseline*1.25]
 random.Random(20261011+repeat).shuffle(order)
 if repeat==0:order.sort(key=lambda c:c['id']!='fw-baseline')
 for config in order:
  target=root/(config['id']+'-r'+str(repeat)+'.json');t=time.perf_counter()
  env=os.environ.copy();env.update(OMP_NUM_THREADS=str(config['threads']),OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS=str(config['threads']))
  print('TRIAL',repeat,config['id'],flush=True)
  result=subprocess.run([sys.executable,'scripts/trial.py','--config',json.dumps(config),'--output',str(target)],env=env,timeout=2400)
  trials.append({'config':config['id'],'repeat':repeat,'returncode':result.returncode,'process_wall_seconds':time.perf_counter()-t})
  (root/'trials.json').write_text(json.dumps(trials,indent=2))
  # Export incremental evidence; final workflow also exports on failure.
  if os.environ.get('GITHUB_TOKEN'):
   from publish import publish
   publish('outputs','runs/'+os.environ['GITHUB_RUN_ID'])
if any(x['returncode'] for x in trials):sys.exit(1)
