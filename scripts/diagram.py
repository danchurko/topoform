#!/usr/bin/env python3
"""Validate a diagram model and compile an offline HTML viewer. Python stdlib only."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'
ID = re.compile(r'^[A-Za-z][A-Za-z0-9_.:-]{0,95}$')
RESERVED = {'root', '__proto__', 'prototype', 'constructor', 'toString', 'toLocaleString', 'valueOf', 'hasOwnProperty', 'isPrototypeOf', 'propertyIsEnumerable', '__defineGetter__', '__defineSetter__', '__lookupGetter__', '__lookupSetter__'}
TOP = {'schemaVersion', 'title', 'description', 'nodes', 'edges', 'views', 'layout', 'metadata'}
NODE = {'id', 'label', 'kind', 'parent', 'icon', 'description', 'tags', 'metadata', 'links', 'evidence'}
EDGE = {'id', 'source', 'target', 'label', 'kind', 'directed', 'description', 'tags', 'metadata', 'links', 'evidence'}
VIEW = {'id', 'label', 'nodeIds', 'edgeKinds'}
LAYOUT = {'direction', 'spacing', 'layerSpacing'}

def safe_url(value, schemes=('http', 'https')) -> bool:
    if not isinstance(value,str) or re.search(r'[\x00-\x20\\]',value):return False
    try:url=urllib.parse.urlsplit(value)
    except ValueError:return False
    return url.scheme in schemes and bool(url.hostname) and not url.username and not url.password

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json(path: Path):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError(f'Duplicate JSON key: {key}')
            obj[key] = value
        return obj
    def invalid(v):
        raise ValueError(f'Non-finite JSON number: {v}')
    def number(v):
        out = float(v)
        if not math.isfinite(out): raise ValueError(f'Non-finite JSON number: {v}')
        return out
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=pairs, parse_constant=invalid, parse_float=number)

def validate(model, icon_ids=None) -> dict:
    errors, warnings = [], []
    def issue(code, subject, message, warning=False):
        (warnings if warning else errors).append({'code': code, 'subject': subject, 'message': message})
    def obj(value, allowed, subject):
        if not isinstance(value, dict):
            issue('TYPE', subject, 'Expected an object.'); return False
        for k in value.keys() - allowed:
            issue('UNKNOWN_FIELD', subject+'.'+k, 'Unsupported field; place domain data in metadata. No silent port/routing promises.')
        return True
    def text(value, subject, required=False, limit=20000):
        if not isinstance(value, str) or (required and not value.strip()) or (isinstance(value,str) and len(value)>limit):
            issue('TEXT', subject, f'Expected {"non-empty " if required else ""}text, at most {limit} characters.'); return False
        return True
    def strings(value, subject):
        if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
            issue('TYPE', subject, 'Expected an array of non-empty strings.'); return False
        if len(value) != len(set(value)): issue('DUPLICATE_VALUE', subject, 'Values must be unique.')
        return True
    def ident(value, subject):
        if not isinstance(value,str) or not ID.fullmatch(value) or value in RESERVED:
            issue('ID',subject,'Use a stable letter-led ID with letters, digits, dot, colon, underscore or hyphen; root/prototype names are reserved.'); return False
        return True
    if not obj(model,TOP,'$'): return {'ok':False,'errors':errors,'warnings':warnings}
    if type(model.get('schemaVersion')) is not int or model['schemaVersion'] != 1: issue('SCHEMA_VERSION','schemaVersion','Expected 1.')
    text(model.get('title'),'title',True,200)
    for k in ['description']:
        if k in model: text(model[k],k)
    if 'metadata' in model and not isinstance(model['metadata'],dict): issue('TYPE','metadata','Expected an object.')
    layout=model.get('layout',{})
    if obj(layout,LAYOUT,'layout'):
        if layout.get('direction','RIGHT') not in ['RIGHT','DOWN','LEFT','UP']: issue('DIRECTION','layout.direction','Expected RIGHT, DOWN, LEFT or UP.')
        for k,minimum in [('spacing',30),('layerSpacing',60)]:
            if k in layout and (type(layout[k]) not in [int,float] or not math.isfinite(layout[k]) or not minimum<=layout[k]<=1000): issue('SPACING','layout.'+k,f'Expected a finite number from {minimum} to 1000.')
    nodes,edges=model.get('nodes'),model.get('edges')
    if not isinstance(nodes,list) or not isinstance(edges,list):
        issue('TYPE','$','nodes and edges must be arrays.');return {'ok':False,'errors':errors,'warnings':warnings}
    if len(nodes)>1000 or len(edges)>4000: issue('SIZE_LIMIT','$','This interactive document is limited to 1000 nodes / 4000 edges. Split into views/artifacts; benchmark a dedicated worker-based app for larger graphs.')
    ids=set(); nmap={}
    for typ,items,fields in [('nodes',nodes,NODE),('edges',edges,EDGE)]:
        for i,item in enumerate(items):
            s=f'{typ}[{i}]'
            if not obj(item,fields,s): continue
            if ident(item.get('id'),s+'.id'):
                if item['id'] in ids: issue('DUPLICATE_ID',s+'.id','Node and edge IDs share one namespace.')
                ids.add(item['id'])
                if typ=='nodes': nmap[item['id']]=item
            if typ=='nodes':
                text(item.get('label'),s+'.label',True,500)
                if 'parent' in item: ident(item['parent'],s+'.parent')
                if 'icon' in item:
                    if text(item['icon'],s+'.icon',True,100) and icon_ids is not None and item['icon'] not in icon_ids:
                        issue('ICON_UNKNOWN',s+'.icon','Unknown icon. Import a licensed local SVG or omit icon; do not silently substitute a brand.')
            else:
                ident(item.get('source'),s+'.source');ident(item.get('target'),s+'.target')
                if 'directed' in item and not isinstance(item['directed'],bool): issue('TYPE',s+'.directed','Expected boolean.')
            for k in ['label','kind','description']:
                if k in item: text(item[k],s+'.'+k, k=='kind')
            if 'tags' in item: strings(item['tags'],s+'.tags')
            if 'metadata' in item and not isinstance(item['metadata'],dict): issue('TYPE',s+'.metadata','Expected an object.')
            if 'evidence' in item:
                ev=item['evidence']
                if obj(ev,{'status','source'},s+'.evidence'):
                    if ev.get('status') not in ['observed','declared','inferred','proposed']: issue('EVIDENCE',s+'.evidence.status','Use observed, declared, inferred or proposed.')
                    if 'source' in ev: text(ev['source'],s+'.evidence.source',True)
                    if ev.get('status')=='observed' and not ev.get('source'): issue('EVIDENCE',s+'.evidence.source','Observed claims need a source reference.')
            if 'links' in item:
                if not isinstance(item['links'],list): issue('TYPE',s+'.links','Expected an array.')
                else:
                    for j,link in enumerate(item['links']):
                        ls=f'{s}.links[{j}]'
                        if obj(link,{'label','url'},ls):
                            text(link.get('label'),ls+'.label',True)
                            url=link.get('url','')
                            if not safe_url(url): issue('LINK_SCHEME',ls+'.url','Only explicit HTTP(S) links without credentials or control characters are permitted.')
            if isinstance(item.get('label'),str) and len(item['label'])>(72 if typ=='nodes' else 35):
                issue('LONG_LABEL',s+'.label','Label is long. Inspect wrapping and crossings; preserve meaning or move detail to description.',True)
    for nid,node in nmap.items():
        p=node.get('parent')
        if p is not None and isinstance(p,str):
            if p not in nmap: issue('PARENT_MISSING',nid,'Parent does not exist.')
            elif nmap[p].get('kind')!='group': issue('PARENT_KIND',nid,'Parent must have kind="group".')
        seen={nid}; cur=node; depth=0
        while isinstance(cur.get('parent'),str) and cur['parent'] in nmap:
            p=cur['parent'];depth+=1
            if p in seen: issue('PARENT_CYCLE',nid,'Containment must be an acyclic single-parent tree.');break
            if depth>12: issue('NESTING_LIMIT',nid,'More than 12 containment levels; create a separate detail view.');break
            seen.add(p);cur=nmap[p]
        if node.get('kind')=='group' and not any(n.get('parent')==nid for n in nmap.values()):
            issue('EMPTY_GROUP',nid,'An empty group is not a compound node. Remove it or represent the empty container as an ordinary node.')
    for e in edges:
        if not isinstance(e,dict):continue
        for k in ['source','target']:
            v=e.get(k)
            if isinstance(v,str) and v not in nmap: issue('ENDPOINT_MISSING',e.get('id','?'),f'{k} does not exist.')
            elif isinstance(v,str) and nmap[v].get('kind')=='group': issue('GROUP_ENDPOINT',e.get('id','?'),'Connect to a concrete member/interface node, not a boundary. Ancestor/group endpoint semantics are unsupported in this baseline.')
        if e.get('source')==e.get('target'): issue('SELF_LOOP',e.get('id','?'),'Supported; inspect the loop label and nearby nodes.',True)
    views=model.get('views',[])
    if not isinstance(views,list): issue('TYPE','views','Expected an array.')
    else:
        vids={'all'}
        for i,v in enumerate(views):
            s=f'views[{i}]'
            if not obj(v,VIEW,s):continue
            if ident(v.get('id'),s+'.id'):
                if v['id'] in vids: issue('DUPLICATE_VIEW',s+'.id','View IDs must be unique; all is reserved.')
                vids.add(v['id'])
            text(v.get('label'),s+'.label',True)
            if strings(v.get('nodeIds'),s+'.nodeIds'):
                for n in v['nodeIds']:
                    if n not in nmap:issue('VIEW_NODE',s+'.nodeIds',f'Unknown node {n}.')
            if 'edgeKinds' in v:strings(v['edgeKinds'],s+'.edgeKinds')
    if len(nodes)>45: issue('DENSE_VIEW','$','More than 45 nodes: create focused views and inspect fit-to-screen text size.',True)
    return {'ok':not errors,'errors':errors,'warnings':warnings,'counts':{'nodes':len(nodes),'edges':len(edges)}}

SVG_TAGS={'svg','g','path','rect','circle','ellipse','line','polyline','polygon','title','desc'}
SVG_ATTRS={'width','height','viewBox','fill','stroke','stroke-width','stroke-linecap','stroke-linejoin','stroke-miterlimit','fill-rule','clip-rule','opacity','fill-opacity','stroke-opacity','d','x','y','x1','x2','y1','y2','cx','cy','r','rx','ry','points','transform','version'}

def sanitize_svg(text: str) -> str:
    """Fail-closed safe static SVG subset; deliberately NOT a general SVG sanitizer."""
    if len(text.encode())>100_000: raise ValueError('SVG exceeds 100 KB.')
    if re.search(r'<!DOCTYPE|<!ENTITY|<\?',text,re.I): raise ValueError('DTD/entities/processing instructions are not accepted.')
    root=ET.fromstring(text)
    if root.tag not in ['svg','{http://www.w3.org/2000/svg}svg']:raise ValueError('Expected an SVG root.')
    for el in root.iter():
        tag=el.tag
        if tag.startswith('{http://www.w3.org/2000/svg}'):tag=tag.split('}',1)[1]
        if tag not in SVG_TAGS:raise ValueError(f'Unsupported SVG tag {tag}. Use flattened static paths.')
        for k,v in el.attrib.items():
            if k not in SVG_ATTRS: raise ValueError(f'Unsupported SVG attribute {k}.')
            if re.search(r'url\s*\(|javascript:|data:|https?:|var\s*\(',v,re.I):raise ValueError('SVG resource/CSS references are not allowed.')
            if 'currentcolor' in v.lower():el.set(k,re.sub('currentcolor','#334155',v,flags=re.I))
        el.tag=tag
    vb=root.get('viewBox','').split()
    if len(vb)!=4:raise ValueError('SVG needs a four-number viewBox.')
    try: nums=[float(x) for x in vb]
    except ValueError:raise ValueError('Invalid viewBox.')
    if not all(math.isfinite(v) for v in nums) or not all(0<v<=10000 for v in nums[2:]):raise ValueError('Invalid SVG dimensions.')
    root.set('xmlns','http://www.w3.org/2000/svg')
    root.set('width',str(nums[2]));root.set('height',str(nums[3]))
    return ET.tostring(root,encoding='unicode')

def local_file(root: Path, relative: str) -> Path:
    p=(root/relative).resolve()
    if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('Asset path must stay within its directory and name an existing file.')
    return p

def icons_payload(model, icon_dir: Path):
    manifest=read_json(icon_dir/'manifest.json');payload={};credits=[]
    for name in sorted({n['icon'] for n in model['nodes'] if 'icon' in n}):
        entry=manifest[name]
        for k in ['path','source','license','attribution','sha256']:
            if not isinstance(entry.get(k),str) or not entry[k]:raise ValueError(f'Icon {name} lacks {k}.')
        if not safe_url(entry['source'],('https',)):
            raise ValueError(f'Icon {name} source must be a safe HTTP(S) provenance URL.')
        raw=local_file(icon_dir,entry['path']).read_bytes()
        if digest(raw)!=entry['sha256']:raise ValueError(f'Icon integrity mismatch: {name}')
        svg=sanitize_svg(raw.decode('utf-8'))
        # The header is trusted constant; arbitrary DTD input is rejected above.
        svg='<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE svg>'+svg
        payload[name]='data:image/svg+xml;charset=utf-8,'+urllib.parse.quote(svg,safe='')
        credits.append({'id':name,**{k:entry.get(k,'') for k in ['pack','version','source','license','attribution','modifications']}})
    return payload,credits

def safe_json(value):
    return json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')

def vendor_payload():
    directory=ROOT/'assets/vendor'; manifest=read_json(directory/'manifest.json');scripts=[];notices=[]
    for item in manifest['files']:
        p=local_file(directory,item['path']);data=p.read_bytes()
        if digest(data)!=item['sha256']:raise ValueError(f'Vendor integrity mismatch: {item["path"]}. Re-vendor explicitly and retest.')
        if item['path'].endswith('.js'):
            scripts.append(re.sub(r'</script',r'<\\/script',data.decode('utf-8'),flags=re.I))
        else:notices.append(data.decode('utf-8'))
    return '\n;\n'.join(scripts),'\n\n'.join(notices),manifest

def atomic_write(path:Path, text:str):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:f.write(text)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)

def build(model, output:Path, icon_dir:Path, raw:bytes):
    manifest=read_json(icon_dir/'manifest.json');report=validate(model,set(manifest))
    if not report['ok']:return report
    icons,credits=icons_payload(model,icon_dir)
    scripts,notices,vendor=vendor_payload()
    template=(ROOT/'assets/viewer.html').read_text()
    runtime=(ROOT/'assets/viewer.js').read_text()
    placeholders={'__TITLE__':html.escape(model['title']),'__MODEL__':safe_json(model),'__ICONS__':safe_json(icons),'__CREDITS__':safe_json(credits),'__NOTICES__':html.escape(notices),'__VENDOR__':scripts,'__RUNTIME__':runtime}
    # One-pass replacement: data cannot introduce a second substitution marker.
    result=re.sub('|'.join(re.escape(k) for k in placeholders),lambda m:placeholders[m.group()],template)
    atomic_write(output,result)
    report.update({'command':'build','version':VERSION,'artifact':str(output.resolve()),'artifactSha256':digest(result.encode()),'modelSha256':digest(raw),'artifactBytes':len(result.encode()),'libraries':vendor['versions'],'browserEvidence':'not-run','visualReview':'not-run'})
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    for cmd in ['validate','build']:
        c=sub.add_parser(cmd);c.add_argument('model',type=Path);c.add_argument('--icons',type=Path,default=ROOT/'assets/icons')
        if cmd=='build':c.add_argument('output',type=Path)
    sub.add_parser('doctor');sub.add_parser('icons')
    args=p.parse_args()
    try:
        if args.command=='doctor':
            _,_,manifest=vendor_payload()
            report={'ok':True,'version':VERSION,'python':sys.version.split()[0],'libraries':manifest['versions'],'runtime':'offline; no npm install required'}
        elif args.command=='icons':report={'ok':True,'icons':read_json(ROOT/'assets/icons/manifest.json')}
        else:
            raw=args.model.read_bytes();model=read_json(args.model)
            if args.command=='validate':report=validate(model,set(read_json(args.icons/'manifest.json')))
            else:
                if args.model.resolve()==args.output.resolve():raise ValueError('Input and output paths must differ.')
                report=build(model,args.output,args.icons,raw)
        print(json.dumps(report,ensure_ascii=False,indent=2));return 0 if report['ok'] else 1
    except (OSError,ValueError,TypeError,KeyError,ET.ParseError) as exc:
        print(json.dumps({'ok':False,'errors':[{'code':'BUILD_ERROR','subject':args.command,'message':str(exc)}]}));return 1
if __name__=='__main__':sys.exit(main())
