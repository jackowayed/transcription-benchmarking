import urllib.request,urllib.parse,json,subprocess,os,pathlib
out={'hardware':subprocess.check_output(['lscpu'],text=True),'affinity':sorted(os.sched_getaffinity(0)),'podcasts':[]}
for query in ['Served with Andy Roddick','404 Media']:
 url='https://itunes.apple.com/search?'+urllib.parse.urlencode({'term':query,'media':'podcast','limit':5})
 with urllib.request.urlopen(url,timeout=30) as r: results=json.load(r)['results']
 out['podcasts'] += [{k:x.get(k) for k in ['collectionName','feedUrl','collectionId']} for x in results]
pathlib.Path('discovery').mkdir(exist_ok=True)
pathlib.Path('discovery/report.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
