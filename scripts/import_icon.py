#!/usr/bin/env python3
"""Import a reviewed local SVG into an icon registry. No downloading or implicit license inference."""
from pathlib import Path
import argparse,json,sys
import diagram

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('svg',type=Path);p.add_argument('--id',required=True);p.add_argument('--source',required=True);p.add_argument('--license',required=True);p.add_argument('--attribution',required=True);p.add_argument('--pack',default='custom');p.add_argument('--version',default='unknown');p.add_argument('--icons',type=Path,required=True);a=p.parse_args()
 try:
  if not diagram.ID.fullmatch(a.id) or a.id in diagram.RESERVED:raise ValueError('Invalid icon ID.')
  if not diagram.safe_url(a.source,('https',)):raise ValueError('Source must be an explicit HTTPS provenance URL.')
  if not a.license.strip() or not a.attribution.strip():raise ValueError('License and attribution must be explicit.')
  svg=diagram.sanitize_svg(a.svg.read_text(encoding='utf-8'))+'\n'
  a.icons.mkdir(parents=True,exist_ok=True);manifest=a.icons/'manifest.json';m=diagram.read_json(manifest) if manifest.exists() else {}
  target=a.icons/(a.id+'.svg')
  if a.id in m or target.exists():raise ValueError('Icon already exists; use a new versioned ID or review/update the registry explicitly.')
  # Manifest is committed last. A crash can leave only an unreferenced SVG, not a bad reference.
  diagram.atomic_write(target,svg)
  m[a.id]={'path':target.name,'source':a.source,'license':a.license,'attribution':a.attribution,'pack':a.pack,'version':a.version,'modifications':'Static allowlist normalisation; explicit viewBox dimensions; currentColor resolved to #334155.','sha256':diagram.digest(svg.encode())}
  diagram.atomic_write(manifest,json.dumps(m,indent=2)+'\n');print(json.dumps({'ok':True,'id':a.id,'manifest':str(manifest)}));return 0
 except Exception as e:print(json.dumps({'ok':False,'errors':[str(e)]}));return 1
if __name__=='__main__':sys.exit(main())
