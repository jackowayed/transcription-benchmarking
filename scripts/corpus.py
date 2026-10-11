"""Freeze recent episodes once, with audio hashes and original-time clip offsets."""
import urllib.request,xml.etree.ElementTree as ET,json,pathlib,hashlib,subprocess,datetime
FEEDS={'served':'https://feeds.megaphone.fm/VMP6052759157','404media':'https://feeds.megaphone.fm/TBIEA2761282490'}

def download(url,path):
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'transcription-benchmark/1.0'}),timeout=120) as r,open(path,'wb') as f:
  import shutil
  shutil.copyfileobj(r,f)

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def prepare(out='data'):
 root=pathlib.Path(out);root.mkdir(exist_ok=True); clips=[];episodes=[]
 for show,feed in FEEDS.items():
  with urllib.request.urlopen(feed,timeout=60) as r:xml=r.read()
  (root/(show+'.rss')).write_bytes(xml)
  items=ET.fromstring(xml).findall('./channel/item')
  eligible=[x for x in items if x.find('enclosure') is not None]
  # The newest full-length episode; skip trailers using declared RSS duration.
  def duration(x):
   s=x.findtext('{http://www.itunes.com/dtds/podcast-1.0.dtd}duration','0')
   try:
    n=0
    for v in s.split(':'):n=n*60+float(v)
    return n
   except ValueError:return 0
  item=next(x for x in eligible if duration(x)>=1200)
  url=item.find('enclosure').attrib['url'];mp3=root/(show+'.mp3');download(url,mp3)
  actual=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(mp3)],text=True))
  episode={'show':show,'title':item.findtext('title'),'published':item.findtext('pubDate'),'guid':item.findtext('guid'),'url':url,'feed':feed,'duration':actual,'source_sha256':sha(mp3)}
  episodes.append(episode)
  # Include pre-roll, three editorial/midroll windows, and closing promotions.
  windows=[('opening',0,180),('early',actual*.25,120),('middle',max(0,actual*.5-240),480),('late',actual*.75,120),('ending',max(0,actual-90),90)]
  for kind,start,length in windows:
   name=show+'-'+kind;path=root/(name+'.wav')
   subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(mp3),'-ss',str(start),'-t',str(length),'-ac','1','-ar','16000','-c:a','pcm_s16le',str(path)],check=True)
   import wave
   with wave.open(str(path)) as w:seconds=w.getnframes()/w.getframerate()
   clips.append({'id':name,'show':show,'kind':kind,'offset':start,'duration':seconds,'path':str(path),'sha256':sha(path)})
 manifest={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'episodes':episodes,'clips':clips}
 (root/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2));return manifest
if __name__=='__main__':prepare()
