"""Publish small benchmark reports to a separate branch; audio stays in artifacts."""
import urllib.request,urllib.error,json,os,pathlib,base64

def api(path,method='GET',body=None):
 req=urllib.request.Request('https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+path,method=method,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+os.environ['GITHUB_TOKEN'],'Accept':'application/vnd.github+json','Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)

def publish(directory,prefix):
 branch=os.environ.get('RESULTS_BRANCH','benchmark-results')
 try:parent=api('/git/ref/heads/'+branch)['object']['sha']
 except urllib.error.HTTPError as e:
  if e.code!=404:raise
  parent=os.environ['GITHUB_SHA'];api('/git/refs','POST',{'ref':'refs/heads/'+branch,'sha':parent})
 tree=api('/git/commits/'+parent)['tree']['sha'];entries=[]
 for p in pathlib.Path(directory).rglob('*'):
  if p.is_file() and p.suffix in {'.json','.jsonl','.txt','.csv','.md'}:
   blob=api('/git/blobs','POST',{'content':base64.b64encode(p.read_bytes()).decode(),'encoding':'base64'})
   entries.append({'path':prefix+'/'+str(p.relative_to(directory)),'mode':'100644','type':'blob','sha':blob['sha']})
 newtree=api('/git/trees','POST',{'base_tree':tree,'tree':entries})
 commit=api('/git/commits','POST',{'message':'Benchmark report: '+prefix,'tree':newtree['sha'],'parents':[parent]})
 api('/git/refs/heads/'+branch,'PATCH',{'sha':commit['sha']})

if __name__=='__main__':
 import sys
 publish(sys.argv[1],sys.argv[2])
