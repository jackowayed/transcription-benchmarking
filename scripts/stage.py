"""Keep setup diagnostics with the exported evidence even before trials exist."""
import subprocess,sys,pathlib,json,time
root=pathlib.Path('outputs');root.mkdir(exist_ok=True);name=sys.argv[1];started=time.perf_counter()
result=subprocess.run(sys.argv[2:],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(root/(name+'.txt')).write_text(result.stdout);(root/(name+'.json')).write_text(json.dumps({'command':sys.argv[2:],'seconds':time.perf_counter()-started,'returncode':result.returncode},indent=2))
print(result.stdout);sys.exit(result.returncode)
