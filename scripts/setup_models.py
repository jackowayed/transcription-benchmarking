import json,pathlib,time,urllib.request,subprocess,hashlib,tarfile,importlib.metadata
from huggingface_hub import snapshot_download
configs=json.loads(pathlib.Path('configs.json').read_text());root=pathlib.Path('models');root.mkdir(exist_ok=True);out={}
def fetch(url,path):
 if not path.exists():
  with urllib.request.urlopen(url,timeout=180) as r,open(path,'wb') as f:
   import shutil;shutil.copyfileobj(r,f)
for c in configs:
 key=c['backend']+':'+c['model']
 if key in out:continue
 t=time.perf_counter()
 if c['backend']=='faster-whisper':
  repo='Systran/faster-whisper-'+c['model'];path=snapshot_download(repo);info={'path':path,'repository':repo,'revision':pathlib.Path(path).name}
 elif c['backend']=='whisper.cpp':
  path=root/('ggml-'+c['model']+'.bin');fetch('https://huggingface.co/ggerganov/whisper.cpp/resolve/main/'+path.name,path)
  info={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 else:
  archive=root/(c['model']+'.tar.bz2');url='https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/'+archive.name;fetch(url,archive)
  with tarfile.open(archive) as tar:tar.extractall(root,filter='data')
  path=root/c['model'];info={'path':str(path),'url':url,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
 info['setup_seconds']=time.perf_counter()-t;out[key]=info
 print(key,info,flush=True)
# Native VAD is recorded as a different segmentation implementation.
vad=root/'ggml-silero-v6.2.0.bin';fetch('https://huggingface.co/ggml-org/whisper-vad/resolve/main/'+vad.name,vad)
out['cpp_vad']={'path':str(vad),'sha256':hashlib.sha256(vad.read_bytes()).hexdigest()}
(root/'manifest.json').write_text(json.dumps(out,indent=2))
