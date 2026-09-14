#!/usr/bin/env python3
"""Build a candidate, browser-check it, then atomically replace the delivery HTML.
Does not claim visual approval: an agent/person must open the saved screenshots.
"""
from pathlib import Path
import argparse,json,os,sys,tempfile
import diagram
import browser_check

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('model',type=Path);p.add_argument('output',type=Path);p.add_argument('--evidence',required=True,type=Path);p.add_argument('--icons',type=Path,default=diagram.ROOT/'assets/icons');p.add_argument('--load',choices=['file','content'],default='file');a=p.parse_args()
 candidate=None;promoted=False
 try:
  if a.model.resolve()==a.output.resolve():raise ValueError('Input model and output artifact paths must differ.')
  a.output.parent.mkdir(parents=True,exist_ok=True)
  fd,name=tempfile.mkstemp(prefix='.candidate-',suffix='.html',dir=a.output.parent);os.close(fd);candidate=Path(name)
  r=diagram.build(diagram.read_json(a.model),candidate,a.icons,a.model.read_bytes())
  if not r['ok']:print(json.dumps(r,indent=2));return 1
  check=browser_check.run(candidate,a.evidence,a.load)
  if not check['ok']:check['existingOutput']='not overwritten';print(json.dumps(check,indent=2));return 1
  os.replace(candidate,a.output)
  promoted=True
  r.update(artifact=str(a.output.resolve()),browserEvidence=str((a.evidence/'browser-report.json').resolve()),visualReview='pending: open and inspect screenshots',loadMode=a.load)
  diagram.atomic_write(a.evidence/'delivery-receipt.json',json.dumps(r,indent=2)+'\n')
  print(json.dumps(r,indent=2));return 0
 except Exception as e:print(json.dumps({'ok':False,'errors':[str(e)],'existingOutput':'promoted; receipt write failed' if promoted else 'not overwritten'}));return 1
 finally:
  if candidate and candidate.exists():candidate.unlink()
if __name__=='__main__':sys.exit(main())
