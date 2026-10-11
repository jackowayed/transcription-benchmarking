import urllib.request,json,subprocess,os,xml.etree.ElementTree as ET
print(subprocess.check_output(['lscpu'],text=True))
print('Affinity:',sorted(os.sched_getaffinity(0)))
for query in ['Served with Andy Roddick','404 Media']:
 url='https://itunes.apple.com/search?'+__import__('urllib.parse',fromlist=['urlencode']).urlencode({'term':query,'media':'podcast','limit':5})
 with urllib.request.urlopen(url,timeout=30) as r: results=json.load(r)['results']
 for x in results:print(json.dumps({k:x.get(k) for k in ['collectionName','feedUrl','collectionId']}))
