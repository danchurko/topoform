#!/usr/bin/env python3
"""Stage official browser bundles from already-installed npm packages. Does not download/install or activate them."""
from pathlib import Path
import argparse,json,shutil,sys
import diagram

SPECS=[('cytoscape','dist/cytoscape.min.js','cytoscape.js','cytoscape.LICENSE.txt'),('elkjs','lib/elk.bundled.js','elk.js','elkjs.LICENSE.txt'),('cytoscape-elk','dist/cytoscape-elk.js','cytoscape-elk.js','cytoscape-elk.LICENSE.txt')]

def stage(node_modules:Path,out:Path):
 if out.exists():raise ValueError('Output directory already exists. Use a fresh staging directory; no implicit replacement.')
 files=[];versions={};payload={}
 for package,bundle,target,notice in SPECS:
  root=node_modules/package;meta=diagram.read_json(root/'package.json');versions[package]=meta['version']
  payload[target]=(root/bundle).read_bytes()
  license_file=next((root/p for p in ['LICENSE','LICENSE.md','LICENSE.txt','license','license.md','license.txt'] if (root/p).is_file()),None)
  if not license_file:raise ValueError(f'Missing license file for {package}. Inspect package manually; do not invent a notice.')
  payload[notice]=license_file.read_bytes()
 # Keep icon notice available for the builder's all-license view.
 payload['fontawesome.LICENSE.txt']=(diagram.ROOT/'assets/vendor/fontawesome.LICENSE.txt').read_bytes()
 order=[s[2] for s in SPECS]+[s[3] for s in SPECS]+['fontawesome.LICENSE.txt']
 for name in order:files.append({'path':name,'sha256':diagram.digest(payload[name])})
 manifest={'versions':versions,'profile':'official-npm-candidate-UNTESTED','provenance':{s[0]:f'Copied from installed {s[0]}@{versions[s[0]]}/{s[1]}; see the package manager lockfile for upstream integrity.' for s in SPECS},'files':files}
 out.mkdir(parents=True)
 try:
  for name,data in payload.items():(out/name).write_bytes(data)
  (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 except Exception:
  shutil.rmtree(out);raise
 return {'ok':True,'staged':str(out.resolve()),'versions':versions,'activated':False,'browserEvidence':'not-run','next':'Review licenses/versions, explicitly replace assets/vendor, rerun tests and visual review.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('node_modules',type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
 try:print(json.dumps(stage(a.node_modules,a.out),indent=2));return 0
 except Exception as e:print(json.dumps({'ok':False,'errors':[str(e)]}));return 1
if __name__=='__main__':sys.exit(main())
