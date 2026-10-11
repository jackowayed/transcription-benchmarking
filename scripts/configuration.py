import os,json,pathlib

def selected_configs():
 configs=json.loads(pathlib.Path('configs.json').read_text());selection=os.environ.get('CONFIG_IDS','').strip()
 if not selection:return configs
 names={x.strip() for x in selection.split(',') if x.strip()};names.add('fw-baseline')
 unknown=names-{c['id'] for c in configs}
 if unknown:raise ValueError('Unknown configurations: '+', '.join(sorted(unknown)))
 return [c for c in configs if c['id'] in names]
