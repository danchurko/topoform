#!/usr/bin/env python3
"""Exercise the complete public workflow from an installed Topoform package."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SHOWCASES = ('aws-commerce','oauth-oidc','order-to-cash','ai-retrieval','cicd-rollback','creative-production')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path);p.add_argument('--load',choices=['file','content'],default='file');a=p.parse_args()
 try:
  subprocess.run([sys.executable,ROOT/'scripts/release.py','check',ROOT],check=True)
  subprocess.run([sys.executable,ROOT/'scripts/diagram.py','doctor'],check=True)
  for name in SHOWCASES:
   model=ROOT/f'examples/{name}.json';artifact=a.out/f'{name}.html';evidence=a.out/f'{name}-checks'
   subprocess.run([sys.executable,ROOT/'scripts/diagram.py','validate',model],check=True)
   subprocess.run([sys.executable,ROOT/'scripts/deliver.py',model,artifact,'--evidence',evidence,'--load',a.load],check=True)
  subprocess.run([sys.executable,ROOT/'tests/run_browser.py','--out',a.out/'regression','--load',a.load],check=True)
  report={'ok':True,'installedRoot':str(ROOT),'showcases':len(SHOWCASES),'loadMode':a.load}
 except (OSError,subprocess.CalledProcessError) as exc:report={'ok':False,'errors':[str(exc)]}
 print(json.dumps(report,indent=2));return 0 if report['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
